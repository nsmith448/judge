from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, TemplateView
from judge import models, views

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', TemplateView.as_view(template_name='index.html'), name='index'),
    url(r'^contest/(?P<slug>[-\w]+)/$', views.ContestView.as_view(), name='contest_home'),
    url(r'^contest/(?P<contest>[-\w]+)/(?P<slug>[-\w]+)/$', views.ProblemView.as_view(), name='problem_home'),
    url(r'^contest/(?P<contest>[-\w]+)/(?P<slug>[-\w]+)/attempt/$', views.start_submit, name='problem_start_submit'),
    url(r'^contest/(?P<contest>[-\w]+)/(?P<slug>[-\w]+)/submissions/$', views.ProblemSubmissions.as_view(), name='problem_submissions'),
    url(r'^contest/(?P<contest>[-\w]+)/(?P<slug>[-\w]+)/attempt/(?P<attempt_pk>\d+)/$', views.SubmitView.as_view(), name='problem_submit'),
    url(r'^inputs/(?P<attempt_pk>\d+)/$', views.download_inputfile, name='problem_input_file'),
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': "login.html"}, name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': "/"}, name="logout"),
    url(r'^admin/', include(admin.site.urls)),
)
