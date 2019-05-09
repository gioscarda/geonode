# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2019 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from django.core.management.base import BaseCommand
from argparse import RawTextHelpFormatter
from geonode.layers.models import Layer
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model


class Command(BaseCommand):

    help = """
    Set permissions to resources for users and groups.
    Arguments:
        - users (-u, --users)
        - groups (-g, --groups)
        - resources (-r, --resources)
        - permissions (-p, --permissions)
    At least one user or one group is required.
    If no resources are typed all the layers will be considered.
    At least one permission must be typed.
    Multiple inputs can be typed with comma separator.
    """

    READ_PERMISSIONS = [
        'view_resourcebase'
    ]

    WRITE_PERMISSIONS = [
        'view_resourcebase',
        'change_layer_data',
        'change_layer_style',
        'change_resourcebase_metadata',
    ]

    DOWNLOAD_PERMISSIONS = [
        'view_resourcebase',
        'download_resourcebase'
    ]

    OWNER_PERMISSIONS = [
        'view_resourcebase',
        'change_layer_data',
        'change_layer_style',
        'change_resourcebase_metadata',
        'download_resourcebase',
        'change_resourcebase',
        'delete_resourcebase',
        'change_resourcebase_permissions',
        'publish_resourcebase'
    ]

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = RawTextHelpFormatter
        return parser

    def add_arguments(self, parser):
        parser.add_argument(
            '-r',
            '--resources',
            dest='resources',
            nargs='*',
            type=str,
            default=None,
            help='Resources names for which permissions will be assigned to. '
                 'Default value: None (all the layers will be considered). '
                 'Multiple choices can be typed with comma separator.'
                 'A Note: names with white spaces must be typed inside quotation marks.'
        )
        parser.add_argument(
            '-p',
            '--permission',
            dest='permission',
            type=str,
            default=None,
            help='Permissions to be assigned. '
                 'Allowed values are: read (r), write (w), download (d) and owner (o).'
        )
        parser.add_argument(
            '-u',
            '--users',
            dest='users',
            nargs='*',
            type=str,
            default=None,
            help='Users for which permissions will be assigned to. '
                 'Multiple choices can be typed with comma separator.'
        )
        parser.add_argument(
            '-g',
            '--groups',
            dest='groups',
            nargs='*',
            type=str,
            default=None,
            help='Groups for which permissions will be assigned to. '
                 'Multiple choices can be typed with comma separator.'
        )

    def handle(self, *args, **options):
        # Retrieving the arguments
        resources_names = options.get('resources')
        permissions_name = options.get('permission')
        users_usernames = options.get('users')
        groups_names = options.get('groups')
        # Processing information
        if not resources_names:
            # If resources is None we consider all the existing layer
            resources = Layer.objects.all()
        else:
            try:
                resources = Layer.objects.filter(title__in=resources_names)
            except Layer.DoesNotExist:
                self.stdout.write(
                    'Warning - No resources have been found with these names: {}.'.format(
                        ", ".join(resources_names)
                    )
                )
        if not resources:
            self.stdout.write("No resources have been found. No update operations have been executed.")
        else:
            User = get_user_model()
            # PERMISSIONS
            if not permissions_name:
                self.stdout.write("No permissions have been provided.")
            else:
                permissions = []
                if permissions_name.lower() in ('read', 'r'):
                    permissions = self.READ_PERMISSIONS
                elif permissions_name.lower() in ('write', 'w'):
                    permissions = self.WRITE_PERMISSIONS
                elif permissions_name.lower() in ('download', 'd'):
                    permissions = self.DOWNLOAD_PERMISSIONS
                elif permissions_name.lower() in ('owner', 'o'):
                    permissions = self.OWNER_PERMISSIONS
                if not permissions:
                    self.stdout.write(
                        "Permission must match one of these values: read (r), write (w), download (d), owner (o)."
                    )
                else:
                    if not users_usernames and not groups_names:
                        self.stdout.write(
                            "At least one user or one group must be provided."
                        )
                    else:
                        # USERS
                        users = []
                        if users_usernames:
                            for username in users_usernames:
                                try:
                                    user = User.objects.get(username=username)
                                    users.append(user)
                                except User.DoesNotExist:
                                    self.stdout.write(
                                        'Warning - The user {} does not exists. '
                                        'It has been be skipped.'.format(username)
                                    )
                        # GROUPS
                        groups = []
                        if groups_names:
                            for group_name in groups_names:
                                try:
                                    group = Group.objects.get(name=group_name)
                                    groups.append(group)
                                except Group.DoesNotExist:
                                    self.stdout.write(
                                        'Warning - The group {} does not exists. '
                                        'It has been skipped.'.format(group_name)
                                    )
                        if not users and not groups:
                            self.stdout.write(
                                'Neither users nor groups corresponding to the typed names have been found. '
                                'No update operations have been executed.'
                            )
                        else:
                            # RESOURCES
                            for resource in resources:
                                # Existing permissions on the resource
                                perm_spec = resource.get_all_level_info()
                                self.stdout.write(
                                    "Initial permissions info for the resource {}:\n{}".format(
                                        resource.title, str(perm_spec))
                                )
                                for u in users:
                                    # Check the permission already exists
                                    if u not in perm_spec["users"]:
                                        perm_spec["users"][u] = permissions
                                    else:
                                        u_perms_list = perm_spec["users"][u]
                                        base_set = set(permissions)
                                        target_set = set(u_perms_list)
                                        perm_spec["users"][u] = u_perms_list + list(base_set - target_set)
                                for g in groups:
                                    # Check the permission already exists
                                    if g not in perm_spec["groups"]:
                                        perm_spec["groups"][g] = permissions
                                    else:
                                        g_perms_list = perm_spec["groups"][g]
                                        base_set = set(permissions)
                                        target_set = set(g_perms_list)
                                        perm_spec["groups"][g] = g_perms_list + list(base_set - target_set)
                                # Set final permissions
                                resource.set_permissions(perm_spec)
                                self.stdout.write(
                                    "Permissions successfully updated!\n"
                                    "Final permissions info for the resource {}:\n"
                                    "{}".format(resource.title, str(perm_spec))
                                )
