# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from urllib.parse import urlparse
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
            # Build callback URI deterministically to avoid http/https mismatches
            # behind reverse proxies. Prefer the same scheme/host as the return URL
            # stored in OAuth state (state['f']).
            base_url = False
            if url_return:
                parsed = urlparse(url_return)
                if parsed.scheme and parsed.netloc:
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
            if not base_url:
                base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            if not base_url:
                base_url = request.env['microsoft.service'].get_base_url()
            if not base_url:
                base_url = request.httprequest.url_root.strip('/')
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
