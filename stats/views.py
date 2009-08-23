import re
import datetime

from django.utils import simplejson
from django.conf import settings

from djangopeople.models import Club, KungfuPerson, Style, Country
from djangopeople.utils import render, render_basic
from django.views.decorators.cache import cache_page, never_cache
from django.core.cache import cache
from django.contrib.auth.models import User
from stats.utils import extract_views_from_urlpatterns

from django.utils.decorators import decorator_from_middleware
from django.middleware.cache import CacheMiddleware
class CustomCacheMiddleware(CacheMiddleware):
    def __init__(self, cache_delay=0, *args, **kwargs):
        super(CustomCacheMiddleware, self).__init__(*args, **kwargs)
        self.cache_delay = cache_delay
        
    def process_response(self, request, response):
        if self.cache_delay:
            extra_js = '<script type="text/javascript">var CACHE_CONTROL=%s;</script>' %\
              self.cache_delay
            response.content = response.content.replace(u'</body>',
                                                        u'%s\n</body>' % extra_js)

        response = super(CustomCacheMiddleware, self).process_response(request, response)
        return response

custom_cache_page = decorator_from_middleware(CustomCacheMiddleware)


if settings.DEBUG and 0:
    def cache_page(delay):
        def rendered(view):
            def inner(request, *args, **kwargs):
                return view(request, *args, **kwargs)
            return inner
        return rendered


@custom_cache_page(60 * 60 * 1) # 1 hours
def competitions(request):
    data = dict()
    data.update(_get_competitions_tables())
    return render(request, 'competitions.html', data)
    

def _get_competitions_tables():
    groups = []
    for club in Club.objects.all():
        count = club.kungfuperson_set.count()
        if not count:
            continue
        groups.append({'object':club,
                       'count': count})
    groups.sort(lambda x,y: cmp(y['count'], x['count']))
    clubs_groups_table = _groups_table(groups, 
                                       "Club",
                                       "Members").content
    
    groups = []
    for style in Style.objects.all():
        count = style.kungfuperson_set.count()
        if not count:
            continue
        groups.append({'object': style,
                       'count': count})
    groups.sort(lambda x,y: cmp(y['count'], x['count']))
    styles_groups_table = _groups_table(groups, 
                                       "Style",
                                       "Practioners").content
    
    groups = []
    for country in Country.objects.all():
        count = country.kungfuperson_set.count()
        if not count:
            continue
        groups.append({'object': country,
                       'count': count
                      })
    groups.sort(lambda x,y: cmp(y['count'], x['count']))
    countries_groups_table = _groups_table(groups, 
                                       "Country",
                                       "Citizens").content
    
    groups = []
    for person in KungfuPerson.objects.all():
        count = person.profile_views
        if not count:
            continue
        groups.append({'object': person,
                       'count': count
                      })
    groups.sort(lambda x,y: cmp(y['count'], x['count']))
    profile_views_groups_table = _groups_table(groups,
                                       "Person",
                                       "Profile views").content
    
    data = locals()
    del data['groups']
    del data['count']
    return data

        

def _groups_table(groups, column1_label, column2_label, max_groups=10):
    count_total = sum([x['count'] for x in groups])
    restgroup = {}
    for group in groups[max_groups:]:
        if not restgroup:
            restgroup['name'] = "All others"
            restgroup['count'] = 1
        else:
            restgroup['count'] += 1
    groups = groups[:max_groups]
    return render_basic('_groups_table.html', locals())





def index(request):
    """list all available stats pages"""
    return render(request, 'stats-index.html', locals())


def new_people(request):
    """page that shows a line graph showing the number of new signups
    cummulativively or individual"""
    #blocks = 'monthly'
    
    first_date = User.objects.all().order_by('date_joined')[0].date_joined
    last_date = User.objects.all().order_by('-date_joined')[0].date_joined
    
    buckets = dict()
    
    prev_month = None
    date = first_date
    qs = User.objects.filter(is_staff=False)
    while date < last_date:
        key = date.strftime('%Y%m')
        if key not in buckets:
            buckets[key] = {'year': date.year, 
                            'month': date.month,
                            'month_name': date.strftime('%B'),
                            'date': date,
                            'count': qs.filter(date_joined__year=date.year,
                                               date_joined__month=date.month).count()
                            }
        date = date + datetime.timedelta(days=1)
        
    # turn it into a list
    buckets = [v for v in buckets.values()]
    buckets.sort(lambda x,y: cmp(x['date'], y['date']))
    total_count = sum([x['count'] for x in buckets])
    
    return render(request, 'stats-new-people.html', locals())
    