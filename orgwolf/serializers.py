#######################################################################
# Copyright 2014 Mark Wolf
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

from __future__ import unicode_literals, absolute_import, print_function
import datetime as dt

from rest_framework import serializers
from django.contrib.auth.models import User

from orgwolf.models import AccountAssociation, OrgWolfUser

class UserSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField()

    def get_name(self, user):
        """Return the users full name (or 'Guest' if anonymous)"""
        if user.is_anonymous:
            name = 'Guest'
        else:
            name = "{f_name} {l_name}".format(f_name=user.first_name,
                                              l_name=user.last_name)
        return name

    class Meta:
        model = OrgWolfUser
        fields = ['id', 'name', 'is_staff', 'is_active']

class AccountAssociationSerializer(serializers.ModelSerializer):

    name = serializers.SerializerMethodField('get_plugin_name')

    def get_plugin_name(self, obj):
        return obj.handler.name

    class Meta:
        model = AccountAssociation
