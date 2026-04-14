# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request


class MicrosoftAuth(http.Controller):

    @http.route('/microsoft_account/authentication', type='http', auth="public")
    def oauth2callback(self, **kw):
        """ This route/function is called by Microsoft when user Accept/Refuse the consent of Microsoft """
        state = json.loads(kw.get('state', '{}'))
        service = state.get('s')
        url_return = state.get('f')
        if (not service or (kw.get('code') and not url_return)):
            raise BadRequest()

        if kw.get('code'):
            # Keep callback redirect URI source aligned with the authorization URI
            # built by microsoft_calendar (_microsoft_authentication_url), which
            # relies on microsoft.service.get_base_url(). This avoids protocol
            # mismatches (http/https) when Odoo is behind a reverse proxy.
            base_url = request.env['microsoft.service'].get_base_url() or request.httprequest.url_root.strip('/')
            access_token, refresh_token, ttl = request.env['microsoft.service']._get_microsoft_tokens(
                kw['code'],
                service,
                redirect_uri=f'{base_url}/microsoft_account/authentication'
            )
            request.env.user._set_microsoft_auth_tokens(access_token, refresh_token, ttl)
            return request.redirect(url_return)
        elif kw.get('error'):
            return request.redirect("%s%s%s" % (url_return, "?error=", kw['error']))
        else:
            return request.redirect("%s%s" % (url_return, "?error=Unknown_error"))
