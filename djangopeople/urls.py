import os
from django.conf.urls.defaults import *
from django.conf import settings
from djangopeople import views
from djangopeople.models import KungfuPerson


urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^club/([A-Za-z0-9-]{3,})/$', views.club),
    (r'^style/([A-Za-z0-9-]{3,})/$', views.style),
    (r'^login/$', views.login),
    (r'^logout/$', views.logout),
    (r'^recent/$', views.recent),
    (r'^recover/$', views.lost_password),
    (r'^recover/([a-z0-9]{3,})/([a-f0-9]+)/([a-f0-9]{32})/$',
        views.lost_password_recover),
    (r'^signup/$', views.signup),

    (r'^guess-club-name.json$', views.guess_club_name_json),
    (r'^guess-username.json$', views.guess_username_json),

    (r'^search/$', views.search),
                       
    (r'^([a-z]{2})/$', views.country),
    (r'^([a-z]{2})/sites/$', views.country_sites),
    (r'^([a-z]{2})/(\w+)/$', views.region),
    
    (r'^([a-z0-9]{3,})/$', views.profile),
    (r'^([a-z0-9]{3,})/password/$', views.edit_password),
    (r'^([a-z0-9]{3,})/videos/add/$', views.add_video),
    (r'^([a-z0-9]{3,})/videos/$', views.videos),
    (r'^([a-z0-9]{3,})/club/delete/([a-z0-9-]{3,})/$', views.delete_club_membership),
    (r'^([a-z0-9]{3,})/style/delete/([a-z0-9-]{3,})/$', views.delete_style),
    (r'^([a-z0-9]{3,})/videos/delete/(\d+)/$', views.delete_video),
    (r'^([a-z0-9]{3,})/club/$', views.edit_club),
    (r'^([a-z0-9]{3,})/style/$', views.edit_style),
    (r'^([a-z0-9]{3,})/profile/$', views.edit_profile),
    (r'^([a-z0-9]{3,})/location/$', views.edit_location),
    url(r'^([a-z0-9]{3,})/upload/$', views.upload_profile_photo, name="upload_profile_photo"),
    (r'^([a-z0-9]{3,})/upload/done/$', views.upload_done),
)
