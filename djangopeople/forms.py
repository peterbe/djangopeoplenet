import re
from django import forms
from django.forms.forms import BoundField
from django.db.models import ObjectDoesNotExist
from models import KungfuPerson, Country, Region, User, RESERVED_USERNAMES
from groupedselect import GroupedChoiceField
from constants import SERVICES, IMPROVIDERS

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    import warnings
    warnings.warn("BeautifulSoup not installed (easy_install BeautifulSoup)")
    BeautifulSoup = None

def region_choices():
    # For use with GroupedChoiceField
    regions = list(Region.objects.select_related().order_by('country', 'name'))
    groups = [(False, (('', '---'),))]
    current_country = False
    current_group = []
    
    for region in regions:
        if region.country.name != current_country:
            if current_group:
                groups.append((current_country, current_group))
                current_group = []
            current_country = region.country.name
        current_group.append((region.code, region.name))
    if current_group:
        groups.append((current_country, current_group))
        current_group = []
    
    return groups

def not_in_the_atlantic(self):
    if self.cleaned_data.get('latitude', '') and self.cleaned_data.get('longitude', ''):
        lat = self.cleaned_data['latitude']
        lon = self.cleaned_data['longitude']
        if 43 < lat < 45 and -39 < lon < -33:
            raise forms.ValidationError("Drag and zoom the map until the crosshair matches your location")
    return self.cleaned_data['location_description']

class SignupForm(forms.Form):

    # Fields for creating a User object
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    username = forms.RegexField('^[a-zA-Z0-9_-]+$', min_length=3, max_length=30)
    password1 = forms.CharField(widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(widget=forms.PasswordInput, required=False)
    
    # Fields for creating a KungfuPerson profile
    bio = forms.CharField(widget=forms.Textarea, required=False)
    trivia = forms.CharField(widget=forms.Textarea, required=False)
    style = forms.CharField(max_length=200, required=False)
    personal_url = forms.URLField(required=False)
    privacy_email = forms.BooleanField(required=False, widget = forms.CheckboxInput)

    # Fields for adding a club membership
    club_url = forms.CharField(max_length=200, required=False)
    club_name = forms.CharField(max_length=200, required=False)
    
    country = forms.ChoiceField(choices = [('', '')] + [
        (c.iso_code, c.name) for c in Country.objects.all()
    ])
    latitude = forms.FloatField(min_value=-90, max_value=90)
    longitude = forms.FloatField(min_value=-180, max_value=180)
    location_description = forms.CharField(max_length=50)
    
    region = GroupedChoiceField(required=False, choices=region_choices())



    
    # Upload a photo is a separate page, because if validation fails we 
    # don't want to tell them to upload it all over again
    #   photo = forms.ImageField(required=False)
    
    # Fields used to create machinetags
    
    # Validation
    def clean_password1(self):
        "Only required if NO openid set for this form"
        if not self.cleaned_data.get('password1', ''):
            raise forms.ValidationError('Password is required')
        return self.cleaned_data['password1']
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1', '')
        password2 = self.cleaned_data.get('password2', '')
        if password1.strip() and password1 != password2:
            raise forms.ValidationError('Passwords must match')
        return self.cleaned_data['password2']
    
    def clean_username(self):
        already_taken = 'That username is unavailable'
        username = self.cleaned_data['username'].lower()
        
        # No reserved usernames, or anything that looks like a 4 digit year 
        if username in RESERVED_USERNAMES or (len(username) == 4 and username.isdigit()):
            raise forms.ValidationError(already_taken)
        
        try:
            user = User.objects.get(username = username)
        except User.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(already_taken)
        
        return username
    
    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email = email)
        except User.DoesNotExist:
            pass
        else:
            raise forms.ValidationError('That e-mail is already in use')
        return email
    
    def clean_region(self):
        # If a region is selected, ensure it matches the selected country
        if self.cleaned_data['region']:
            try:
                region = Region.objects.get(
                    code = self.cleaned_data['region'],
                    country__iso_code = self.cleaned_data['country']
                )
            except ObjectDoesNotExist:
                raise forms.ValidationError(
                    'The region you selected does not match the country'
                )
        return self.cleaned_data['region']

    clean_location_description = not_in_the_atlantic
    
    
    def clean_first_name(self):
        if self.cleaned_data['first_name']:
            v = self.cleaned_data['first_name']
            if v.islower() or v.isupper():
                self.cleaned_data['first_name'] = v.title()
        return self.cleaned_data['first_name']

    def clean_last_name(self):
        if self.cleaned_data['last_name']:
            v = self.cleaned_data['last_name']
            if v.islower() or v.isupper():
                self.cleaned_data['last_name'] = v.title()
        return self.cleaned_data['last_name']


class PhotoUploadForm(forms.Form):
    photo = forms.ImageField()

class AccountForm(forms.Form):
    openid_server = forms.URLField(required=False)
    openid_delegate = forms.URLField(required=False)

class LocationForm(forms.Form):
    country = forms.ChoiceField(choices = [('', '')] + [
        (c.iso_code, c.name) for c in Country.objects.all()
    ])
    latitude = forms.FloatField(min_value=-90, max_value=90)
    longitude = forms.FloatField(min_value=-180, max_value=180)
    location_description = forms.CharField(max_length=50)
    
    region = GroupedChoiceField(required=False, choices=region_choices())
    
    def clean_region(self):
        # If a region is selected, ensure it matches the selected country
        if self.cleaned_data['region']:
            try:
                region = Region.objects.get(
                    code = self.cleaned_data['region'],
                    country__iso_code = self.cleaned_data['country']
                )
            except ObjectDoesNotExist:
                raise forms.ValidationError(
                    'The region you selected does not match the country'
                )
        return self.cleaned_data['region']
    
    clean_location_description = not_in_the_atlantic

class FindingForm(forms.Form):    
    def __init__(self, *args, **kwargs):
        self.person = kwargs.pop('person', 1) # So we can validate e-mail later
        super(FindingForm, self).__init__(*args, **kwargs)

    email = forms.EmailField()
    privacy_email = forms.BooleanField(required=False, widget = forms.CheckboxInput)

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email = email).exclude(kungfuperson = self.person).count() > 0:
            raise forms.ValidationError('That e-mail is already being used') 
        return email

class ProfileForm(forms.Form):
    bio = forms.CharField(widget = forms.Textarea, required=False)
    trivia = forms.CharField(widget = forms.Textarea, required=False)
    personal_url = forms.URLField( required=False)
    club_url = forms.URLField( required=False)
    club_name = forms.CharField(max_length=200, required=False)
    what_is_kungfu = forms.CharField(max_length=144, required=False)

class VideoForm(forms.Form):
    embed_src = forms.CharField(widget=forms.Textarea, required=False)
    description = forms.CharField(widget=forms.Textarea, required=False)
    
    def clean_embed_src(self):
        embed_src = self.cleaned_data['embed_src']
        
        # check the tags it's allowed to contain
        allowed_tags = ('object', 'embed', 'param')
        for tag in re.findall(r'<(\w+)[^>]*>', embed_src):
            if tag not in allowed_tags:
                raise forms.ValidationError("Tag not allowed (<%s>)" % tag)
            
        from HTMLParser import HTMLParseError
        try:
            soup = BeautifulSoup(embed_src.strip())
        except HTMLParseError:
            raise forms.ValidationError("HTML too broken to be parsed")
            
        self.cleaned_data['embed_src'] = str(soup)
        return self.cleaned_data['embed_src']


def make_validator(key, form):
    def check():
        if form.cleaned_data.get(key.replace('url_', 'title_')) and \
            not form.cleaned_data.get(key):
            raise forms.ValidationError, 'You need to provide a URL'
        return form.cleaned_data.get(key)
    return check
