/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onPatched } from "@odoo/owl";

function getMapContainer() {
    return document.getElementById("map-partner-container");
}

function clearMapRetry(controller) {
    if (controller._crmPartnerMapRetryTimer) {
        clearTimeout(controller._crmPartnerMapRetryTimer);
        controller._crmPartnerMapRetryTimer = null;
    }
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.resModel === "res.partner") {
            const renderPartnerMap = () => this._initializePartnerMap();
            onMounted(renderPartnerMap);
            onPatched(renderPartnerMap);
        }
    },

    _initializePartnerMap(retryCount = 0) {
        clearMapRetry(this);
        const mapContainer = getMapContainer();
        if (!mapContainer || this.props.resModel !== "res.partner") {
            return;
        }

        if (typeof L === "undefined") {
            if (retryCount < 20) {
                this._crmPartnerMapRetryTimer = setTimeout(() => {
                    this._initializePartnerMap(retryCount + 1);
                }, 150);
            }
            return;
        }
        this._renderPartnerMap();
    },

    _renderPartnerMap() {
        const mapContainer = getMapContainer();
        const record = this.model?.root;
        if (!mapContainer || !record || record.resModel !== "res.partner") {
            return;
        }

        const partner = record.data || {};
        const street = partner.street || "";
        const city = partner.city || "";
        const state = partner.state_id
            ? (Array.isArray(partner.state_id) ? partner.state_id[1] : partner.state_id)
            : "";
        const country = partner.country_id
            ? (Array.isArray(partner.country_id) ? partner.country_id[1] : partner.country_id)
            : "España";
        const zip = partner.zip || "";
        const fullAddress = [street, zip, city, state, country].filter(Boolean).join(", ");

        mapContainer.innerHTML = "";

        let map;
        try {
            map = L.map(mapContainer).setView([40.4637, -3.7492], 13);
        } catch (error) {
            console.warn("Error inicializando mapa de partner:", error);
            mapContainer.innerHTML = '<p style="color: #999; padding: 20px;">No se pudo cargar el mapa</p>';
            return;
        }

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution: "© OpenStreetMap contributors",
            maxZoom: 19,
        }).addTo(map);

        if (fullAddress && fullAddress.length > 5) {
            this._geocodeAddress(fullAddress, map);
        } else {
            mapContainer.innerHTML += '<p style="color: #999; padding: 10px; font-size: 12px;">Dirección incompleta para geocodificar</p>';
        }
    },

    async _geocodeAddress(address, map) {
        const mapContainer = getMapContainer();
        if (!mapContainer) {
            return;
        }

        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(address)}`,
                {
                    headers: {
                        "User-Agent": "Odoo-Partner-Map/1.0",
                    },
                }
            );
            const data = await response.json();
            if (data && data.length > 0) {
                const result = data[0];
                const lat = parseFloat(result.lat);
                const lon = parseFloat(result.lon);
                map.setView([lat, lon], 15);
                const marker = L.marker([lat, lon]).addTo(map);
                marker.bindPopup(`
                    <div style="font-size: 12px;">
                        <strong>${address}</strong><br/>
                        <small>Lat: ${lat.toFixed(6)}<br/>Lon: ${lon.toFixed(6)}</small>
                    </div>
                `).openPopup();
            } else {
                console.info("Dirección no encontrada para mapa de partner:", address);
            }
        } catch (error) {
            console.warn("Error geocodificando partner:", error);
        }
    },
});
