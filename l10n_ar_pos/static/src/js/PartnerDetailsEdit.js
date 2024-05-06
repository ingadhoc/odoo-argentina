odoo.define("l10n_ar_pos.PartnerDetailsEdit", function (require) {
    "use strict";
    const PartnerDetailsEdit = require("point_of_sale.PartnerDetailsEdit");
    const { patch } = require("web.utils");

    patch(PartnerDetailsEdit.prototype, "l10n_ar_pos", {
        setup() {
            this._super(...arguments);
            if (this.env.pos.isArgentineanCompany()) {
                const partner = this.props.partner;
                this.intFields.push("l10n_ar_afip_responsibility_type_id");
                this.intFields.push("l10n_latam_identification_type_id");
                this.changes.l10n_ar_afip_responsibility_type_id = partner.l10n_ar_afip_responsibility_type_id && partner.l10n_ar_afip_responsibility_type_id[0];
                this.changes.l10n_latam_identification_type_id = partner.l10n_latam_identification_type_id && partner.l10n_latam_identification_type_id[0];
            }
        },
    });

});
