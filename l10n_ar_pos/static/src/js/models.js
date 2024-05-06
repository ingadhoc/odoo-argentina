odoo.define('l10n_ar_pos.models', function (require) {
    "use strict";

var { PosGlobalState, Order } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');


const PosL10nArPosGlobalState = (PosGlobalState) => class PosL10nArPosGlobalState extends PosGlobalState {
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.consumidorFinalAnonimoId = loadedData['consumidor_final_anonimo_id'];
        this.l10n_ar_afip_responsibility_type = loadedData['l10n_ar.afip.responsibility.type'];
        this.l10n_latam_identification_type = loadedData['l10n_latam.identification.type'];
    }
    isArgentineanCompany(){
        return this.company.country.code === 'AR';
    }
}
Registries.Model.extend(PosGlobalState, PosL10nArPosGlobalState);

const L10nARPosOrder = (Order) => class L10nARPosOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
            if (this.pos.isArgentineanCompany()) {
                if (!this.partner) {
                    this.partner = this.pos.db.partner_by_id[this.pos.consumidorFinalAnonimoId];
                }
            }
    }
}
Registries.Model.extend(Order, L10nARPosOrder);

});
