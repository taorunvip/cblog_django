from django.shortcuts import render, redirect, HttpResponse

# Create your views here.
from django.db.models import Count, Avg, Max
from django.contrib import auth

from blog.models import Article, UserInfo, Category, Tag, Article2Tag


def login(request):
    if request.method == "POST":
        user = request.POST.get("user")
        pwd = request.POST.get("pwd")
        user = auth.authenticate(username=user, password=pwd)
        if user:
            auth.login(request, user)
            return redirect("/index/")
    return render(request, "login.html")


def index(request):
    article_list = Article.objects.all()
    return render(request, "index.html", {"article_list": article_list})


def logout(request):
    auth.logout(request)

    return redirect("/index/")


def homesite(request, username, **kwargs):
    """
    查询
    :param request:
    :param username:
    :return:
    """

    print("kwargs", kwargs)

    # 查询当前站点的用户对象
    user = UserInfo.objects.filter(username=username).first()
    if not user:
        return render(request, "not_found.html")
    # 查询当前站点对象
    blog = user.blog

    # 查询当前用户发布的所有文章
    if not kwargs:
        article_list = Article.objects.filter(user__username=username)

    else:
        condition = kwargs.get("condition")
        params = kwargs.get("params")

        if condition == "category":
            article_list = Article.objects.filter(user__username=username).filter(category__title=params)
        elif condition == "tag":
            article_list = Article.objects.filter(user__username=username).filter(tags__title=params)
        else:
            year, month = params.split("/")
            article_list = Article.objects.filter(user__username=username).filter(create_time__year=year,
                                                                                  create_time__month=month)

    if not article_list:
        return render(request, "not_found.html")

    # # 查询当前站点每一个分类的名称以及对应的文章数
    #
    # cate_list=Category.objects.filter(blog=blog).annotate(c=Count("article__title")).values_list("title", "c")
    # print(cate_list)
    #
    # # 查询当前站点每一个标签的名称以及对应的文章数
    #
    # tag_list=Tag.objects.filter(blog=blog).annotate(c=Count("article__title")).values_list("title", "c")
    #
    # # 日期归档
    #
    # date_list=Article.objects.filter(user=user).extra(select={"y_m_date":"strftime('%%Y/%%m',create_time)"}).values("y_m_date").annotate(c=Count("title")).values_list("y_m_date","c")
    # print(date_list)

    return render(request, "homesite.html", locals())


def article_detail(request, username, article_id):
    user = UserInfo.objects.filter(username=username).first()
    # 查询当前站点对象
    blog = user.blog

    article_obj = Article.objects.filter(pk=article_id).first()

    comment_list = Comment.objects.filter(article_id=article_id)

    return render(request, 'article_detail.html', locals())


from blog.models import ArticleUpDown, Comment
import json
from django.http import JsonResponse

from django.db.models import F
from django.db import transaction


def digg(request):
    print(request.POST)
    is_up = json.loads(request.POST.get("is_up"))
    article_id = request.POST.get("article_id")
    user_id = request.user.pk
    response = {"state": True, "msg": None}

    obj = ArticleUpDown.objects.filter(user_id=user_id, article_id=article_id).first()
    if obj:
        response["state"] = False
        response["handled"] = obj.is_up
    else:
        with transaction.atomic():
            new_obj = ArticleUpDown.objects.create(user_id=user_id, article_id=article_id, is_up=is_up)
            if is_up:
                Article.objects.filter(pk=article_id).update(up_count=F("up_count") + 1)
            else:
                Article.objects.filter(pk=article_id).update(down_count=F("down_count") + 1)

    return JsonResponse(response)


def comment(request):
    # 获取数据
    user_id = request.user.pk
    article_id = request.POST.get("article_id")
    content = request.POST.get("content")
    pid = request.POST.get("pid")
    # 生成评论对象
    with transaction.atomic():
        comment = Comment.objects.create(user_id=user_id, article_id=article_id, content=content, parent_comment_id=pid)
        Article.objects.filter(pk=article_id).update(comment_count=F("comment_count") + 1)

    response = {"state": True}
    response["timer"] = comment.create_time.strftime("%Y-%m-%d %X")
    response["content"] = comment.content
    response["user"] = request.user.username

    return JsonResponse(response)


def backend(request):
    user = request.user
    article_list = Article.objects.filter(user=user)
    return render(request, "backend/backend.html", locals())


def add_article(request):
    if request.method == "POST":

        title = request.POST.get("title")
        content = request.POST.get("content")
        user = request.user
        cate_pk = request.POST.get("cate")
        tags_pk_list = request.POST.getlist("tags")

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        # 文章过滤：
        for tag in soup.find_all():
            # print(tag.name)
            if tag.name in ["script", ]:
                tag.decompose()

        # 切片文章文本
        desc = soup.text[0:150]

        article_obj = Article.objects.create(title=title, content=str(soup), user=user, category_id=cate_pk, desc=desc)

        for tag_pk in tags_pk_list:
            Article2Tag.objects.create(article_id=article_obj.pk, tag_id=tag_pk)

        return redirect("/backend/")


    else:

        blog = request.user.blog
        cate_list = Category.objects.filter(blog=blog)
        tags = Tag.objects.filter(blog=blog)
        return render(request, "backend/add_article.html", locals())


from cblog_django import settings
import os


def upload(request):
    print(request.FILES)
    obj = request.FILES.get("upload_img")
    name = obj.name

    path = os.path.join(settings.BASE_DIR, "static", "upload", name)
    with open(path, "wb") as f:
        for line in obj:
            f.write(line)

    import json

    res = {
        "error": 0,
        "url": "/static/upload/" + name
    }

    return HttpResponse(json.dumps(res))
