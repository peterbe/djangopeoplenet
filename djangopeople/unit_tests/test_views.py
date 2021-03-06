"""
testing views
"""
import os, re
from django.utils import simplejson
from django.conf import settings
from django.utils import simplejson
from django.core import mail


from djangopeople.models import KungfuPerson, Club, Country, Style, \
  DiaryEntry, Photo, Recruitment
from djangopeople import views
from testbase import TestCase

_original_PROWL_API_KEY = settings.PROWL_API_KEY

class ViewsTestCase(TestCase):
    
    def tearDown(self):
        # delete any upload thumbnails
        thumbnails_root = os.path.join(settings.MEDIA_ROOT,
                                       'photos', 
                                       'upload-thumbnails')
        if os.path.isdir(thumbnails_root):
            for f in os.listdir(thumbnails_root):
                f = os.path.join(thumbnails_root, f)
                if os.path.isdir(f):
                    for filename in os.listdir(f):
                        if os.path.isfile(os.path.join(f, filename)):
                            os.remove(os.path.join(f, filename))
                    if not os.listdir(f):
                        os.rmdir(f)
            if not os.listdir(thumbnails_root):
                os.rmdir(thumbnails_root)
        
        # delete any 
        for dir_ in [x.get_person_upload_folder() for x in KungfuPerson.objects.all()]:
            if os.path.isdir(dir_):
                for f in os.listdir(dir_):
                    if os.path.isfile(os.path.join(dir_, f)):
                        os.remove(os.path.join(dir_, f))
                if not os.listdir(dir_):
                    os.rmdir(dir_)
        
        # Delete any photos so their their uploaded mock photos are deleted
        Photo.objects.all().delete()
        
        super(ViewsTestCase, self).tearDown()
    
    
    def test_guess_club_name(self):
        """Test signup"""
        
        response = self.client.get('/guess-club-name.json?club_url=')
        assert response.status_code==200
        result = simplejson.loads(response.content)
        self.assertTrue('error' in result)
        self.assertTrue('club_name' not in result)
        
        # add a club
        Club.objects.create(name=u"Fujian White Crane",
                            url=u"http://www.fwckungfu.com")
        
        # spelling it without http
        response = self.client.get('/guess-club-name.json?club_url=www.fwckungfu.com')
        assert response.status_code==200
        result = simplejson.loads(response.content)
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        
        # spelling it without http
        response = self.client.get('/guess-club-name.json?club_url=www.fwckungfu.com')
        assert response.status_code==200
        result = simplejson.loads(response.content)
        self.assertTrue('error' not in result)
        self.assertEqual(result['club_name'], u"Fujian White Crane")
        
        # spelling it with http:// and /index.html
        response = self.client.get('/guess-club-name.json?club_url=http://www.fwckungfu.com/index.html')
        assert response.status_code==200
        result = simplejson.loads(response.content)
        self.assertTrue('error' not in result)
        self.assertEqual(result['club_name'], u"Fujian White Crane")
        
    def test_guess_club_name_remotely(self):
        """test guessing a club name by downloading the <title> for the URL"""
        
        def run(url):
            response = self.client.get('/guess-club-name.json?club_url=%s' % url)
            assert response.status_code==200
            return simplejson.loads(response.content)

        examples_dir = os.path.join(os.path.dirname(__file__), 'example_kung_sites')
        def get_url(filename):
            return "file://" + os.path.join(examples_dir, filename)
        
        result = run(get_url("fwc.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"Fujian White Crane Kung Fu Club")
        
        result = run(get_url("kamonwingchun.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"Kamon Martial Art Federation")
        
        result = run(get_url("kungfulondon.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"Hung Leng Kuen Kung Fu, London")
                
        result = run(get_url("shaolintemplateuk.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"Shaolin Temple UK")
        
        result = run(get_url("wengchun.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"London Shaolin Weng Chun Kung Fu Academy")
        
        result = run(get_url("wingchun-escrima.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"Tao Wing Chun & Escrima Academy  London & Surrey")
        
        #result = run(get_url(""))
        #self.assertTrue('error' not in result)
        #self.assertTrue('club_name' in result)
        #self.assertEqual(result['club_name'], u"")
        
        result = run(get_url("namyang.html"))
        self.assertTrue('error' not in result)
        self.assertTrue('club_name' in result)
        self.assertEqual(result['club_name'], u"Shaolin Martial Arts: Nam Yang Kung Fu")
        
        
    
    def test_signup_basic(self):
        """test posting to signup"""
        # load from fixtures
        example_country = Country.objects.all().order_by('?')[0]
        
        response = self.client.post('/signup/', 
                                    dict(username='bob',
                                         email='bob@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                        ))
        self.assertEqual(response.status_code, 302)
        
        self.assertEqual(KungfuPerson.objects.\
           filter(user__username="bob").count(), 1)
        
        if settings.PROWL_API_KEY:
            # this should have posted to prowl
            posted_prowl = self._get_posted_prowls()[-1]
            self.assertTrue('Bob Sponge' in posted_prowl['description'])
        
    def test_signup_with_utmz_cookie(self):
        """set a cookie called __utmz like Google Analytics does and the 
        value of this should end up in KungfuPerson.came_from
        """
        example_country = Country.objects.all().order_by('?')[0]
        utmz = '186359603.1250807267.14.4.utmcsr=forum.kungfumagazine.com|'\
               'utmccn=(referral)|utmcmd=referral|utmcct=/forum/showthread.php'
        response = self.client.get('/')
        
        self.client.cookies['__utmz'] = utmz
        response = self.client.post('/signup/',
                                    dict(username='bob',
                                         email='bob@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                        ))
        self.assertEqual(response.status_code, 302)
        person = KungfuPerson.objects.get(user__username="bob")
        
        self.assertTrue(person.came_from)
        self.assertTrue(person.came_from.count('forum.kungfumagazine.com'))
        self.assertTrue(person.came_from.count('referral'))
        self.assertTrue(person.came_from.count('/forum/showthread.php'))
        
        self.client.logout()
        
        utmz = '186359603.1250808317.14.5.utmcsr=google|utmccn=(organic)|utmcmd='\
               'organic|utmctr=kung%20fu%20people'
        self.client.cookies['__utmz'] = utmz
        
        response = self.client.post('/signup/',
                                    dict(username='bob2',
                                         email='bob2@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob2",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                        ))
        self.assertEqual(response.status_code, 302)
        person = KungfuPerson.objects.get(user__username="bob2")
        
        self.assertTrue(person.came_from)
        self.assertTrue(person.came_from.count('google'))
        self.assertTrue(person.came_from.count('organic'))
        self.assertTrue(person.came_from.count('kung%20fu%20people'))

        self.client.logout()
        
        utmz = '186359603.1250862268.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'
        self.client.cookies['__utmz'] = utmz
        
        response = self.client.post('/signup/',
                                    dict(username='bob3',
                                         email='bob3@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob3",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                        ))
        self.assertEqual(response.status_code, 302)
        person = KungfuPerson.objects.get(user__username="bob3")
        
        self.assertFalse(person.came_from)


    def test_signup_multiple_styles(self):
        """test posting to signup and say that you have multiple styles
        by entering it with a comma"""
        
        # load from fixtures
        example_country = Country.objects.all().order_by('?')[0]
        
        response = self.client.post('/signup/', 
                                    dict(username='bob',
                                         email='bob@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                         style=u"Fat style, Chocolate rain"
                                        ))
        self.assertEqual(response.status_code, 302)
        
        self.assertEqual(KungfuPerson.objects.\
           filter(user__username="bob").count(), 1)
        
        # This should now have created 2 styles
        self.assertEqual(Style.objects.all().count(), 2)
        self.assertEqual(Style.objects.filter(name="Fat style").count(), 1)
        self.assertEqual(Style.objects.filter(name="Chocolate rain").count(), 1)
        
    def test_signup_style_with_paranthesis(self):
        """test posting to signup and say that you have a style with a bracket
        then the slug shouldn't break
        """
        # load from fixtures
        example_country = Country.objects.all().order_by('?')[0]
        
        response = self.client.post('/signup/', 
                                    dict(username='bob',
                                         email='bob@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                         style=u"Fat style (as in Phat!)"
                                        ))
        self.assertEqual(response.status_code, 302)
        
        self.assertEqual(KungfuPerson.objects.\
           filter(user__username="bob").count(), 1)
        
        # This should now have created 2 styles
        self.assertEqual(Style.objects.all().count(), 1)
        self.assertEqual(Style.objects.filter(name="Fat style (as in Phat!)").count(), 1)
        style = Style.objects.all()[0]
        self.assertEqual(style.slug, 'fat-style-as-in-phat')
        self.assertEqual(style.get_absolute_url(),
                         '/style/fat-style-as-in-phat/')
        
        # now try to add another style with a bracket in it
        response = self.client.get('/bob/style/')
        assert response.status_code == 200
        self.assertTrue('Your current style' in response.content)
        self.assertTrue('/style/fat-style-as-in-phat/' in response.content)
        self.assertTrue('/bob/style/delete/fat-style-as-in-phat/' in response.content)
        
        # add another one
        response = self.client.post('/bob/style/', 
                                    dict(style_name=u"dim (sung)"))
        self.assertEqual(response.status_code, 302)
        style2 = Style.objects.get(name__icontains=u'dim')
        self.assertEqual(style2.name, u'dim (sung)')
        self.assertEqual(style2.slug, u'dim-sung')
        self.assertEqual(style2.get_absolute_url(), u'/style/dim-sung/')
        
        response = self.client.get('/bob/style/')
        assert response.status_code == 200
        self.assertTrue('Your current styles' in response.content)
        self.assertTrue('/style/dim-sung/' in response.content)


    def test_signup_with_recruitment(self):
        """Image you came to the site by the URL 
        http://kungfupeople.com/?rc=1
        then that means that user with ID 1 recruited you.
        This information is kept in a session variable.
        """
        user, person = self._create_person('billy', 'billy@example.com')
        recruiter_id = user.id
        
        self.client.get('/', dict(rc=user.id))
        # the session should have been set up now
        
        example_country = Country.objects.all().order_by('?')[0]
        
        response = self.client.post('/signup/', 
                                    dict(username='bob',
                                         email='bob@example.org',
                                         password1='secret',
                                         password2='secret',
                                         first_name=u"Bob",
                                         last_name=u"Sponge",
                                         region='',
                                         country=example_country.iso_code,
                                         latitude=1.0,
                                         longitude=-1.0,
                                         location_description=u"Hell, Pergatory",
                                         style=u"Fat style, Chocolate rain"
                                        ))
        self.assertEqual(response.status_code, 302)
        
        self.assertEqual(KungfuPerson.objects.\
           filter(user__username="bob").count(), 1)
        
        self.assertEqual(Recruitment.objects.count(), 1)
        recruitment = Recruitment.objects.all()[0]
        self.assertEqual(recruitment.recruiter, user)
        self.assertEqual(recruitment.recruited, 
                         KungfuPerson.objects.get(user__username="bob").user)

    def test_newsletter_options(self):
        """test changing your newsletter options"""
        
        user, person = self._create_person('bob', 'bob@example.com')
        
        default = person.newsletter
        
        # change it to plain
        response = self.client.post('/bob/newsletter/options/',
                                    dict(newsletter='plain'))
        self.assertEqual(response.status_code, 403) # forbidden
        
        #self.client.login(username="bob", password="secret")
        self.client.post('/login/', dict(username="bob", password="secret"))
        
        r=self.client.get('/')
        response = self.client.post('/bob/newsletter/options/',
                                    dict(newsletter='plain'))
        
        # THIS DOES NOT WORK!!!
        # WHY IS THE LOGIN NOT TAKING EFFECT?????
        self.assertEqual(response.status_code, 302) # redirect
        
    def test_diary_entry_location_json(self):
        """test getting the json for a diary entry"""
        
        country = Country.objects.all().order_by('?')[0]

        user, person = self._create_person('bob', 'bob@example.com',
                                           password="secret")
        # that person has to have a diary entry
        entry = DiaryEntry.objects.create(user=user, title=u"Title",
                                          slug="title",
                                          content=u"Content",
                                          is_public=True,
                                          country=country,
                                          latitude=2.2,
                                          longitude=-1.1,
                                          location_description=u"Hell")
        
        response = self.client.get(entry.get_absolute_url()+'location.json')
        self.assertEqual(response.status_code, 403) # because you're not logged in
        
        # but if you log in it should be ok
        self.client.login(username="bob", password="secret")
        
        response = self.client.get(entry.get_absolute_url()+'location.json')
        self.assertEqual(response.status_code, 200)
        
        data = simplejson.loads(response.content)
        self.assertEqual(data['latitude'], 2.2)
        self.assertEqual(data['longitude'], -1.1)
        self.assertEqual(data['country'], country.iso_code)
        self.assertEqual(data['location_description'], u"Hell")
        
    def test_photo_upload_multiple_basic(self):
        """add a couple of photos first into the upload folder then
        run /username/photo/upload/ with some description and some
        location.
        """
        country = Country.objects.all().order_by('?')[0]

        user, person = self._create_person('bob', 'bob@example.com',
                                           password="secret")
        
        # by default the photo/upload/ page will expect you to use
        # the swfupload
        self.client.login(username="bob", password="secret")
        
        upload_url = person.get_absolute_url() + 'photo/upload/'
        response = self.client.get(upload_url)
        assert response.status_code == 200
        self.assertFalse(response.content.count('type="file"'))
        
        # now upload some photos to the pre/ method
        pre_upload_url = upload_url + 'pre/'
        photo1 = open(os.path.join(os.path.dirname(__file__), 'P1000898.jpg'))
        photo2 = open(os.path.join(os.path.dirname(__file__), 'P1010051.jpg'))
        from django.core.files import File
        file1 = File(photo1)
        file2 = File(photo2)
        
        response = self.client.post(pre_upload_url, dict(Filename='P1000898.jpg',
                                                         Filedata=file1))
        self.assertEqual(response.status_code, 200)
        # response.content is now a url to a thumbnail
        thumbnail_url = response.content
        self.assertTrue(thumbnail_url.endswith('.jpg'))
        
        # the actual file is located in...
        file_path = os.path.join(settings.MEDIA_ROOT, 
                                thumbnail_url.replace('/static/',''))
        # you can view this
        image_response = self.client.get(thumbnail_url)
        
        assert image_response.status_code == 200
        import stat
        self.assertEqual(len(image_response.content), 
                         os.stat(file_path)[stat.ST_SIZE])
        
        # upload another one
        response = self.client.post(pre_upload_url, dict(Filename='P1010051.jpg',
                                                         Filedata=file2))
        
        # there should now be two temporary photos uploaded
        self.assertEqual(len(os.listdir(person.get_person_upload_folder())), 2)
        
        self.assertEqual(Photo.objects.filter(user=user).count(), 0)
        # Now, continue with submitting the photo upload form
        photo_upload_url = person.get_absolute_url() + 'photo/upload/'
        response = self.client.post(photo_upload_url, 
                                    dict(country=country.iso_code,
                                         location_description=u"Hell",
                                         latitude=1.0,
                                         longitude=-2.0,
                                         description=u"Some description"
                                        ))
        self.assertEqual(response.status_code, 302)
        redirected_to = response._headers['location'][1]
        self.assertTrue(redirected_to.endswith('/bob/'))
        
        self.assertEqual(Photo.objects.filter(user=user).count(), 2)
        for photo in Photo.objects.filter(user=user):
            self.assertEqual(photo.location_description, u"Hell")
            self.assertEqual(photo.country, country)
            self.assertEqual(photo.latitude, 1.0)
            self.assertEqual(photo.longitude, -2.0)
            
        
    def test_photo_upload_single_basic(self):
        """same as test_photo_upload_multiple_basic
        but this time prefer with single.
        """
        country = Country.objects.all().order_by('?')[0]

        user, person = self._create_person('bob', 'bob@example.com',
                                           password="secret")
        
        # by default the photo/upload/ page will expect you to use
        # the swfupload
        self.client.login(username="bob", password="secret")
        
        upload_url = person.get_absolute_url() + 'photo/upload/'
        response = self.client.get(upload_url, dict(prefer='single'))
        assert response.status_code == 200
        self.assertTrue(response.content.count('type="file"'))

        photo1 = open(os.path.join(os.path.dirname(__file__), 'P1000898.jpg'))
        photo2 = open(os.path.join(os.path.dirname(__file__), 'P1010051.jpg'))
        from django.core.files import File
        file1 = File(photo1)
        
        self.assertEqual(Photo.objects.filter(user=user).count(), 0)
        # Now, continue with submitting the photo upload form
        photo_upload_url = person.get_absolute_url() + 'photo/upload/'
        response = self.client.post(photo_upload_url, 
                                    dict(country=country.iso_code,
                                         location_description=u"Hell",
                                         latitude=1.0,
                                         longitude=-2.0,
                                         description=u"Some description",
                                         photo=file1,
                                        ))
        self.assertEqual(response.status_code, 302)
        redirected_to = response._headers['location'][1]
        self.assertTrue(redirected_to.endswith('/bob/')) # back to profile
        
    def test_find_clubs_by_location(self):
        """ by a lat,lng you should be able to find a list of possible clubs
        """
        # some examples to work with
        # Place, Country, latitude, longitude
        # Fuzhou, Fujian, 26.0740535325, 119.292297363
        # Islington, England, 51.532601866, -0.108382701874 
        # Euston, England,  51.527475885, -0.128552913666
        # Geneva, Switzerland, 46.20217114444467, 6.142730712890625
        # Saint-Genis-Pouilly, France, 46.244451065485094, 6.0225677490234375
        
        switzerland = Country.objects.get(name=u"Switzerland")
        france = Country.objects.get(name=u"France")
        uk = Country.objects.get(name=u"United Kingdom")
        
        
        user1, person1 = self._create_person("user1", "user1@example.com",
                                             country=switzerland.name,
                                             latitude=46.20217114444467,
                                             longitude=6.142730712890625,
                                             location_description=u"Geneva")
        doggy_style = self._create_club(u"Doggy Style")
        person1.club_membership.add(doggy_style)

        user2, person2 = self._create_person("user2", "user2@example.com",
                                             country=france.name,
                                             latitude=46.244451065485094,
                                             longitude=6.0225677490234375,
                                             location_description=u"Saint-Genis-Pouilly")
        wing_chun = self._create_club(u"Wing Chun Club")
        person2.club_membership.add(wing_chun)
        

        user3, person3 = self._create_person("user3", "user3@example.com",
                                             country=uk.name,
                                             latitude=51.532601866,
                                             longitude=-0.108382701874,
                                             location_description=u"Islington")

        person3.club_membership.add(wing_chun)
        white_crane = self._create_club(u"FWC White Crane")
        
        user4, person4 = self._create_person("user4", "user4@example.com",
                                             country=uk.name,
                                             latitude=51.527475885,
                                             longitude=-0.128552913666,
                                             location_description=u"Euston")
        
        person4.club_membership.add(white_crane)
        
        func = views._find_clubs_by_location
        
        # by distance, Saint-Genis-Pouilly is very close to Geneva, Switzerland
        # first by searching really really close to Geneva to make sure the sorting
        # is right
        clubs = func(dict(latitude=46.202, longitude=6.142), within_range=40)
        self.assertEqual(clubs, [doggy_style, wing_chun])

        # but if you include the country it should only find the one in that country
        clubs = func(dict(latitude=46.202, longitude=6.142), country="switzerland")
        self.assertEqual(clubs, [doggy_style])
        
        # Search in Kings cross which it between Euston and Islington
        clubs = func(dict(latitude=51.53079, longitude=-0.121021))
        self.assertEqual(clubs, [white_crane, wing_chun])
        
        # adding country wont help
        clubs = func(dict(latitude=51.53079, longitude=-0.121021), country="GB")
        self.assertEqual(clubs, [white_crane, wing_chun])
        
        clubs = func(dict(latitude=51.53079, longitude=-0.121021), country="GB", 
                     location_description="islington")
        self.assertEqual(clubs, [wing_chun])
        
        # try the same searches but with the json interface
        def func(location, country=None,
                 location_description=None,
                 within_range=None):
            params = dict(latitude=location['latitude'], 
                          longitude=location['longitude'])
            if country is not None:
                params['country'] = country
            if location_description is not None:
                params['location_description'] = location_description
            if within_range is not None:
                params['within_range'] = within_range
            
            response = self.client.get('/find-clubs-by-location.json', params)
            assert response.status_code == 200
            return simplejson.loads(response.content)
        
        clubs = func(dict(latitude=46.202, longitude=6.142), within_range=40)
        self.assertEqual(len(clubs), 2)
        self.assertEqual([x['name'] for x in clubs],
                          [u'Doggy Style', u'Wing Chun Club'])
        
        
    def test_zoom_content(self):
        """zoom in on a region and expect to find people there"""
        
        
        # some examples to work with
        # Place, Country, latitude, longitude
        # Fuzhou, Fujian, 26.0740535325, 119.292297363
        # Islington, England, 51.532601866, -0.108382701874 
        # Euston, England,  51.527475885, -0.128552913666
        # Geneva, Switzerland, 46.20217114444467, 6.142730712890625
        # Saint-Genis-Pouilly, France, 46.244451065485094, 6.0225677490234375
        
        switzerland = Country.objects.get(name=u"Switzerland")
        france = Country.objects.get(name=u"France")
        uk = Country.objects.get(name=u"United Kingdom")
        
        
        user1, person1 = self._create_person("user1", "user1@example.com",
                                             country=switzerland.name,
                                             latitude=46.20217114444467,
                                             longitude=6.142730712890625,
                                             location_description=u"Geneva")
        doggy_style = self._create_club(u"Doggy Style")
        person1.club_membership.add(doggy_style)
        masturbated = self._create_diary_entry(user1, u"Masturbated",
                                               u"That was fun",
                                               is_public=False,
                                               country=switzerland.name,
                                               latitude=46.20217114444467,
                                               longitude=6.142730712890625,
                                               location_description=u"Geneva")


        user2, person2 = self._create_person("user2", "user2@example.com",
                                             country=france.name,
                                             latitude=46.244451065485094,
                                             longitude=6.0225677490234375,
                                             location_description=u"Saint-Genis-Pouilly")
        wing_chun_club = self._create_club(u"Wing Chun Club")
        person2.club_membership.add(wing_chun_club)
        wing_chun = self._create_style(u"Wing Chun")
        person2.styles.add(wing_chun)
        got_flexible = self._create_diary_entry(user2, u"Got flexible",
                                                u"More flexible now",
                                                country=france.name,
                                                latitude=46.244451065485094,
                                                longitude=6.0225677490234375,
                                                location_description=u"Saint-Genis-Pouilly"
                                               )
        

        user3, person3 = self._create_person("user3", "user3@example.com",
                                             country=uk.name,
                                             latitude=51.532601866,
                                             longitude=-0.108382701874,
                                             location_description=u"Islington")

        person3.club_membership.add(wing_chun_club)
        
        white_crane = self._create_club(u"FWC White Crane")
        user4, person4 = self._create_person("user4", "user4@example.com",
                                             country=uk.name,
                                             latitude=51.527475885,
                                             longitude=-0.128552913666,
                                             location_description=u"Euston")
        
        person4.club_membership.add(white_crane)
        
        # north east of Ireland
        north_west = (56.13330691237569, -14.47998046875)
        # Koln, Germany
        south_east = (50.84757295365389, 6.943359375)
        
        # the people we expect inside this box are the UK people/clubs only
        in_box = KungfuPerson.objects.in_box((north_west[0], north_west[1],
                                              south_east[0], south_east[1]))
        
        self.assertEqual([x.id for x in in_box], 
                         [x.id for x in [person3, person4]])
        
        # north of Lyon, France and west of Bern, Switzerland
        north_west = (46.830133640447386, 5.2294921875)
        # slightly north west of Milano, Italy
        south_east = (45.54483149242463, 8.525390625)
        
        # the people we expect inside this box are the France, Switzerland people
        in_box = KungfuPerson.objects.in_box((north_west[0], north_west[1],
                                              south_east[0], south_east[1]))
        self.assertEqual([x.id for x in in_box], 
                         [x.id for x in [person1, person2]])
        
        
        # test zoom_content_json
        response = self.client.get('/zoom-content.json',
                                    dict(left=north_west[0], upper=north_west[1],
                                         right=south_east[0], lower=south_east[1]))
        
        self.assertEqual(response.status_code, 200)
        content = simplejson.loads(response.content)
        # we expect two people
        self.assertEqual(len(content['people']), 2)
        # two clubs
        self.assertEqual(len(content['clubs']), 2)
        # one style
        self.assertEqual(len(content['styles']), 1)
        # one diary entry
        self.assertEqual(len(content['diary_entries']), 1)
        
        
    def test_lost_password(self):
        """when you click on lost password it should send an email which will
        contain a link back to the site"""
        switzerland = Country.objects.get(name=u"Switzerland")
        user, person = self._create_person("user1", "user1@example.com",
                                           country=switzerland.name,
                                           latitude=46.20217114444467,
                                           longitude=6.142730712890625,
                                           location_description=u"Geneva",
                                           first_name="Userino")

        #print KungfuPerson.objects.all()
        response = self.client.get('/recover/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Enter your username' in response.content)
        
        # you have to post a variable called 'username'
        response = self.client.post('/recover/', dict(username='NOOOPE'))
        self.assertTrue('That was not a valid username' in response.content)

        response = self.client.post('/recover/', dict(username='User1'))
        # this should now have sent out an email
        self.assertEquals(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual("%s password recovery" % settings.PROJECT_NAME, 
                         email.subject)

        self.assertTrue('Userino' in email.body)
        self.assertTrue(settings.PROJECT_NAME in email.body)
        recover_url = None
        # all the urls in the email body should be openable
        for url in re.findall(r'(http://.*?)[\s\.]', email.body):
            if url.count('/recover/'):
                recover_url = url
            else:
                r = self.client.get(url)
                self.assertTrue(r.status_code in (200, 302))
                
        self.assertTrue(recover_url)
            
        self.assertTrue('e-mail has been sent' in response.content)
        self.assertTrue(user.email in response.content)
        
        # before we open the actual recover link, check that you can't try
        # to recover the password again.
        response = self.client.post('/recover/', dict(username='User1'))
        self.assertTrue('Recovery instructions already sent' in response.content)
        self.assertTrue('Please try again a bit later' in response.content)
        
        # now, let's try to do the actual recover
        response = self.client.get(recover_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response._headers['location'])
        
    def test_add_style_whitespace_and_case_insensitive(self):
        """you should be able to enter your style with excess whitespace
        and in the different case and that shouldn't create a new style object
        """
        switzerland = Country.objects.get(name=u"Switzerland")
        user, person = self._create_person("user1", "user1@example.com",
                                           country=switzerland.name,
                                           latitude=46.20217114444467,
                                           longitude=6.142730712890625,
                                           location_description=u"Geneva",
                                           first_name="Userino")
        # log in as this person because otherwise you can't edit your style
        self.client.login(username="user1", password="secret")
        
        self.assertEqual(Style.objects.count(), 0)
        # add the first style
        response = self.client.post('/user1/style/', dict(style_name='Fat style'))
        assert response.status_code == 302
        self.assertEqual(Style.objects.count(), 1)
        
        response = self.client.post('/user1/style/', dict(style_name='fat style'))
        assert response.status_code == 302
        self.assertEqual(Style.objects.count(), 1)
        
        response = self.client.post('/user1/style/', dict(style_name='fat STYLE '))
        assert response.status_code == 302
        self.assertEqual(Style.objects.count(), 1)
        
        
