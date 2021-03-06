#######################################################################
# Copyright 2012 Mark Wolf
#
# This file is part of OrgWolf.
#
# OrgWolf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#######################################################################

from django import forms
from django.contrib.auth import authenticate
from orgwolf.models import OrgWolfUser as User

class UserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(),
        label="New Password")
    password_2 = forms.CharField(
        widget=forms.PasswordInput(),
        label="Password Again")
    class Meta:
        model = User
        fields = ('password',)
    def clean(self):
        # Make sure both password fields are the same
        data = self.cleaned_data
        if data.get('password') != data.get('password_2'):
            raise forms.ValidationError('Passwords do not match')
        return self.cleaned_data

class PasswordForm(UserForm):
    old_password = forms.CharField(
        widget=forms.PasswordInput(),
        label="Old Password")
    class Meta:
        model = User
        fields = ('old_password', 'password', 'password_2')
    def clean_old_password(self):
        """Make sure the old password is valid. Requires self.user to be set"""
        old_pass = self.cleaned_data['old_password']
        user = self.user
        username = user.username
        if not authenticate(username=username, password=old_pass):
            raise forms.ValidationError('Incorrect password')

class RegistrationForm(UserForm):
    class Meta:
        model = User
        fields = ('username', 'password')

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
            'preferred_timezone',
            )
