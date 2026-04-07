FROM odoo:18.0

USER root
RUN rm -rf /usr/lib/python3/dist-packages/odoo/addons

COPY ./addons /usr/lib/python3/dist-packages/odoo/addons
USER odoo
