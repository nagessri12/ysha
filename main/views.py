import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from .models import User, FriendRequest, Post, Message, Like, Comment, Notification
from django.views.decorators.csrf import csrf_exempt

# ------------------ TEMPLATE VIEWS ------------------ #

def splash(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'splash.html')

def auth_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'auth.html')

@login_required
def home(request):
    friend_ids = FriendRequest.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & Q(status='accepted')
    ).values_list('sender_id', 'receiver_id')
    f_set = set()
    for s, r in friend_ids:
        f_set.add(s); f_set.add(r)
    f_set.discard(request.user.id)

    online_users = User.objects.filter(is_online=True, id__in=f_set)
    
    recent_messages = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')
    chat_ids = set()
    for m in recent_messages:
        chat_ids.add(m.sender_id if m.receiver_id == request.user.id else m.receiver_id)
    
    recent_users = User.objects.filter(id__in=chat_ids, is_online=True).exclude(id__in=request.user.blocked_users.values_list('id', flat=True))
    notif_count = FriendRequest.objects.filter(receiver=request.user, status='pending').count()
    
    return render(request, 'chat_list.html', {
        'online_users': online_users,
        'recent_users': recent_users,
        'notif_count': notif_count
    })

@login_required
def chat_window(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if not other_user.is_online:
        return redirect('home')
    return render(request, 'chat_window.html', {'other_user': other_user})

@login_required
def friend_profile(request, user_id):
    friend = get_object_or_404(User, id=user_id)
    friends_count = FriendRequest.objects.filter(
        (Q(sender=friend) | Q(receiver=friend)) & Q(status='accepted')
    ).count()
    posts_count = Post.objects.filter(user=friend).count()
    
    freq = FriendRequest.objects.filter(
        (Q(sender=request.user) & Q(receiver=friend)) | 
        (Q(sender=friend) & Q(receiver=request.user))
    ).first()
    
    status = freq.status if freq else None
    is_sender = freq.sender == request.user if freq else False

    return render(request, 'friend_profile.html', {
        'friend': friend, 
        'friends_count': friends_count, 
        'posts_count': posts_count,
        'rel_status': status,
        'is_sender': is_sender
    })

@login_required
def profile_view(request):
    friends_count = FriendRequest.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & Q(status='accepted')
    ).count()
    posts_count = Post.objects.filter(user=request.user).count()
    return render(request, 'profile.html', {'user': request.user, 'friends_count': friends_count, 'posts_count': posts_count})

@login_required
def discover_view(request):
    tab = request.GET.get('tab', 'global')
    if tab == 'my_posts':
        posts = Post.objects.filter(user=request.user).order_by('-created_at')
    elif tab == 'friends':
        friend_ids = FriendRequest.objects.filter(
            (Q(sender=request.user) | Q(receiver=request.user)) & Q(status='accepted')
        ).values_list('sender_id', 'receiver_id')
        ids = set()
        for s, r in friend_ids:
            ids.add(s); ids.add(r)
        ids.discard(request.user.id)
        posts = Post.objects.filter(Q(user_id__in=ids) | Q(user=request.user)).order_by('-created_at')
    else:
        posts = Post.objects.filter(visibility='global').order_by('-created_at')
        
    for p in posts:
        p.is_liked = p.likes.filter(user=request.user).exists()
        p.like_count = p.likes.count()
        p.comment_list = p.comments.all().order_by('created_at')

    friend_ids = FriendRequest.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & Q(status='accepted')
    ).values_list('sender_id', 'receiver_id')
    f_set = set()
    for s, r in friend_ids:
        f_set.add(s); f_set.add(r)
    f_set.discard(request.user.id)
    friends = User.objects.filter(id__in=f_set)

    return render(request, 'discover.html', {'posts': posts, 'active_tab': tab, 'friends': friends})

@login_required
def settings_view(request):
    blocked_users = request.user.blocked_users.all()
    return render(request, 'settings.html', {'blocked_users': blocked_users})

@login_required
def notifications_view(request):
    reqs = FriendRequest.objects.filter(receiver=request.user, status='pending')
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'notifications.html', {'requests': reqs, 'notifications': notifs})

@login_required
def add_friend_page(request):
    return render(request, 'add_friend.html')

# ---------- NEW: Dedicated Share Page ----------
@login_required
def share_page(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.visibility == 'private' and post.user != request.user:
        return redirect('discover')
    
    friend_relations = FriendRequest.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & Q(status='accepted')
    ).values_list('sender_id', 'receiver_id')
    
    friend_ids = set()
    for s, r in friend_relations:
        friend_ids.add(s)
        friend_ids.add(r)
    friend_ids.discard(request.user.id)
    
    friends = User.objects.filter(id__in=friend_ids)
    
    return render(request, 'share_page.html', {
        'post': post,
        'friends': friends
    })

# ---------- NEW: Dedicated Comment Page ----------
@login_required
def comment_page(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.visibility == 'private' and post.user != request.user:
        return redirect('discover')
    
    comments = post.comments.filter(parent__isnull=True).order_by('created_at')
    # Prefetch replies
    from django.db.models import Prefetch
    replies = Comment.objects.filter(post=post, parent__isnull=False).select_related('user')
    comment_list = []
    for c in comments:
        c.threaded_replies = [r for r in replies if r.parent_id == c.id]
        comment_list.append(c)
    
    return render(request, 'comment_page.html', {
        'post': post,
        'comments': comment_list,
        'user': request.user
    })

@csrf_exempt
@login_required
def delete_comment_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cid = data.get('comment_id')
            comment = get_object_or_404(Comment, id=cid)
            
            # Permission check: comment author OR post author
            if comment.user == request.user or comment.post.user == request.user:
                comment.delete()
                return JsonResponse({"status": "deleted"})
            else:
                return JsonResponse({"error": "Unauthorized Access"}, status=403)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


# ------------------ API VIEWS ------------------ #

@csrf_exempt
def register_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            if User.objects.filter(Q(username=username) | Q(email=email)).exists():
                return JsonResponse({"error": "User or Email already exists"}, status=400)

            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            user.is_online = True
            user.save()
            return JsonResponse({"message": "Registration successful"}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                user.is_online = True
                user.save()
                return JsonResponse({"message": "Login successful"}, status=200)
            return JsonResponse({"error": "Invalid username or password"}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def logout_view(request):
    request.user.is_online = False
    request.user.save()
    logout(request)
    return redirect('splash')

@login_required
def user_search_api(request):
    query = request.GET.get('q', '')
    if not query: 
        return JsonResponse([], safe=False)
    
    users = User.objects.filter(username__icontains=query).exclude(id=request.user.id)[:10]
    results = []
    for u in users:
        freq = FriendRequest.objects.filter(
            (Q(sender=request.user) & Q(receiver=u)) | 
            (Q(sender=u) & Q(receiver=request.user))
        ).first()
        results.append({
            "id": u.id, "username": u.username,
            "is_requested": True if freq else False,
            "status": freq.status if freq else None
        })
    return JsonResponse(results, safe=False)

@csrf_exempt
@login_required
def send_request_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            uid = data.get('user_id')
            target = get_object_or_404(User, id=uid)
            
            incoming = FriendRequest.objects.filter(sender=target, receiver=request.user, status='pending').first()
            if incoming:
                incoming.status = 'accepted'
                incoming.save()
                return JsonResponse({"message": "Connected"}, status=200)
                
            FriendRequest.objects.get_or_create(sender=request.user, receiver=target)
            return JsonResponse({"message": "Request sent"}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def update_request_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rid = data.get('request_id')
            act = data.get('action')
            req = get_object_or_404(FriendRequest, id=rid, receiver=request.user)
            req.status = act
            req.save()
            return JsonResponse({"message": "Updated"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def upload_post_api(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        visibility = request.POST.get('visibility', 'global')
        if file:
            ftype = 'video' if file.name.lower().endswith(('.mp4', '.mov', '.avi')) else 'image'
            Post.objects.create(user=request.user, media_url=file, file_type=ftype, visibility=visibility)
            return JsonResponse({"message": "Success"}, status=201)
        return JsonResponse({"error": "No file provided"}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def update_profile_api(request):
    if request.method == 'POST':
        request.user.bio = request.POST.get('bio', request.user.bio)
        if 'profile_pic' in request.FILES:
            request.user.profile_pic = request.FILES['profile_pic']
        request.user.save()
        return redirect('profile')
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def update_settings_api(request):
    if request.method == 'POST':
        if 'chat_background' in request.FILES:
            request.user.chat_background = request.FILES['chat_background']
            request.user.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'api' in request.path:
            return JsonResponse({"status": "success"})
        return redirect('settings')
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def delete_post_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pid = data.get('post_id')
            post = get_object_or_404(Post, id=pid, user=request.user)
            post.delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def get_messages_api(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    messages = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) |
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by('created_at')
    
    is_blocked_by_me = request.user.blocked_users.filter(id=other_user.id).exists()
    
    data = []
    for m in messages:
        if is_blocked_by_me and m.sender_id == other_user.id:
            continue
        data.append({
            "sender_id": m.sender_id, 
            "message": m.content,
            "type": m.message_type,
            "media_url": m.media_url.url if m.media_url else None
        })
    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
def send_message_api(request):
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('message', '')
        media = request.FILES.get('media')
        m_type = request.POST.get('type', 'text')
        
        receiver = get_object_or_404(User, id=receiver_id)
        
        if not receiver.is_online:
            return JsonResponse({"error": "Cannot send messages to offline users."}, status=403)
        
        if receiver.blocked_users.filter(id=request.user.id).exists() or request.user.blocked_users.filter(id=receiver.id).exists():
            return JsonResponse({"error": "Communication blocked"}, status=403)

        Message.objects.create(
            sender=request.user, receiver=receiver, 
            content=content, media_url=media, message_type=m_type
        )
        return JsonResponse({"status": "sent"}, status=201)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def toggle_block_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            uid = data.get('user_id')
            other = get_object_or_404(User, id=uid)
            if request.user.blocked_users.filter(id=uid).exists():
                request.user.blocked_users.remove(other)
                return JsonResponse({"status": "unblocked"})
            else:
                request.user.blocked_users.add(other)
                return JsonResponse({"status": "blocked"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def delete_chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            uid = data.get('user_id')
            other = get_object_or_404(User, id=uid)
            Message.objects.filter(
                (Q(sender=request.user) & Q(receiver=other)) |
                (Q(sender=other) & Q(receiver=request.user))
            ).delete()
            return JsonResponse({"status": "deleted"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

# ------------------ LIKE / COMMENT / SHARE APIs ------------------ #

@csrf_exempt
@login_required
def like_post_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pid = data.get('post_id')
            post = get_object_or_404(Post, id=pid)
            like, created = Like.objects.get_or_create(user=request.user, post=post)
            if not created:
                like.delete()
                return JsonResponse({"status": "unliked"})
            
            if post.user != request.user:
                Notification.objects.create(
                    user=post.user, sender=request.user, notif_type='like', post=post,
                    text=f"{request.user.username} liked your post."
                )
            return JsonResponse({"status": "liked", "like_count": post.likes.count()})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
def comment_post_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pid = data.get('post_id')
            txt = data.get('text')
            parent_id = data.get('parent_id')
            
            if not pid or not txt:
                return JsonResponse({"error": "post_id and text are required"}, status=400)
            
            post = get_object_or_404(Post, id=pid)
            parent = get_object_or_404(Comment, id=parent_id) if parent_id else None
            
            comment = Comment.objects.create(user=request.user, post=post, text=txt, parent=parent)
            
            if post.user != request.user:
                Notification.objects.create(
                    user=post.user, sender=request.user, notif_type='comment', post=post,
                    text=f"{request.user.username} commented: {txt[:50]}"
                )
            return JsonResponse({
                "status": "commented",
                "comment": {
                    "id": comment.id,
                    "user": request.user.username,
                    "text": comment.text,
                    "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "parent_id": parent_id
                }
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

@login_required
def get_friends_for_share_api(request):
    friend_relations = FriendRequest.objects.filter(
        (Q(sender=request.user) | Q(receiver=request.user)) & Q(status='accepted')
    ).values_list('sender_id', 'receiver_id')
    
    friend_ids = set()
    for s, r in friend_relations:
        friend_ids.add(s)
        friend_ids.add(r)
    friend_ids.discard(request.user.id)
    
    friends = User.objects.filter(id__in=friend_ids).only('id', 'username')
    data = [{"id": f.id, "username": f.username} for f in friends]
    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
def share_post_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pid = data.get('post_id')
            friend_id = data.get('friend_id')
            
            if not pid or not friend_id:
                return JsonResponse({"error": "post_id and friend_id are required"}, status=400)
                
            post = get_object_or_404(Post, id=pid)
            friend = get_object_or_404(User, id=friend_id)
            
            if friend == request.user:
                return JsonResponse({"error": "Cannot share with yourself"}, status=400)
            
            is_friend = FriendRequest.objects.filter(
                (Q(sender=request.user, receiver=friend) | Q(sender=friend, receiver=request.user)),
                status='accepted'
            ).exists()
            if not is_friend:
                return JsonResponse({"error": "You can only share with friends"}, status=403)
            
            Message.objects.create(
                sender=request.user,
                receiver=friend,
                message_type='post_share',
                content=f"/post/{post.id}",
                media_url=post.media_url
            )
            return JsonResponse({"status": "shared", "message": f"Post shared with {friend.username}"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)