FROM odoo:18.0

USER root
RUN rm -rf /usr/lib/python3/dist-packages/odoo/addons

COPY ./addons /usr/lib/python3/dist-packages/odoo/addons
COPY ./odoo/addons /usr/lib/python3/dist-packages/odoo/addons

COPY ./helpdesk /mnt/extra-addons

USER odoo

RUN echo "list_db = False" >> /etc/odoo/odoo.conf
