# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    Copyright (C) 2015 Novobi LLC (<http://novobi.com>)
#
##############################################################################

import requests
import urllib
import jwt
import time
from odoo.http import request
from odoo.exceptions import UserError
import json

import logging
_logger = logging.getLogger(__name__)


class ZoomServices:
    """
    :param _api_key: api key from Novobi Zoom Marketplace App
    :param _api_secret: api secret from Novobi Zoom Marketplace App
    :param _email: email of user who will be the host
    """
    _api_key = None
    _api_secret = None
    _base_url = 'https://api.zoom.us/v2/'
    _email = None

    def __init__(self, zoom_api_key, zoom_api_secret, zoom_email):
        self._api_key = zoom_api_key
        self._api_secret = zoom_api_secret
        self._email = zoom_email

    def _get_access_token(self):
        """
        Generate JWT token for authorization of Zoom API
        :return signed_token: string of JWT token
        """
        payload = {
            'iss': self._api_key,
            'exp': time.time() + 12000,
        }
        signed_token = jwt.encode(payload, self._api_secret, algorithm='HS256')
        return signed_token.decode('utf-8')

    def get_zoom_header(self):
        """
        Generate Header which will be used in all requests
        :return headers: Dict
        """
        token = self._get_access_token()
        headers = {
            'Content-Type': "application/json",
            'Authorization': 'Bearer {}'.format(token)
        }
        return headers

    def get_meeting_invitation(self, meeting_id):
        """
        Get Zoom meeting invitation
        :return: invitation: Dict
        """
        headers = self.get_zoom_header()
        url = self._base_url + 'meetings/%s/invitation' % meeting_id
        response = requests.get(url, headers=headers)
        invitation = response.json()
        return invitation

    def create_meeting(self, room_info):
        """
        Create Zoom Meeting via Zoom API
        :param room_info: dictionary of room's info for creating new meeting. Ref Zoom API for more detail
        :return meeting_info: dictionary of zoom meeting includes: meeting's id, room's password
        """
        topic = room_info.get('topic')
        start_time = room_info.get('start_time')
        timezone = room_info.get('timezone')
        password = room_info.get('password', False)
        duration = room_info.get('duration')
        data = {
            "topic": topic,
            "type": 2,
            "start_time": start_time,
            "duration": duration,
            "timezone": timezone,
            "settings": {
                "join_before_host": 1,  # allow participant to join meeting before host
                "enforce_login": 0
            }
        }
        if password:
            data.update({"password": password})

        headers = self.get_zoom_header()
        url = self._base_url + '/users/' + self._email

        meeting_info = {}
        response = requests.post(url + '/meetings', headers=headers, json=data)
        if response.status_code != 201:
            raise UserError('Zoom API Error: %s' % response.text)
        else:
            meeting_info = response.json()

        return meeting_info

    def update_meeting(self, meeting_id, values):
        """

        :param meeting_id: zoom meeting's id
        :param values: dictionary of values that need update.
         For more detail, please ref to https://marketplace.zoom.us/docs/api-reference/zoom-api/meetings/meetingupdate
        :return: raise error if modification is not success
        """

        headers = headers = self.get_zoom_header()
        url = self._base_url + '/meetings/' + meeting_id

        response = requests.patch(url, headers=headers, json=values)
        if response.status_code != 204:
            raise UserError('Zoom API Error: %s' % response.text)
        return response

    def delete_meeting(self, meeting_id):
        """
        Delete zoom meeting
        :param meeting_id: zoom meeting's id
        :return: raise error if deletion is not success
        """
        headers = headers = self.get_zoom_header()
        url = self._base_url + '/meetings/' + meeting_id

        result = {}
        response = requests.delete(url, headers=headers)
        if response.status_code != 204 and response.json().get('code') != 3001:
            raise UserError('Zoom API Error: %s' % response.text)
        return result
