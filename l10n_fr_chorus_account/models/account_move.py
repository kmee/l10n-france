# Copyright 2017-2020 Akretion France (http://www.akretion.com)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import logging
import os.path
import tarfile
import time
from io import BytesIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang

logger = logging.getLogger(__name__)

CREDIT_TRF_CODES = ("30", "31", "42")
CHORUS_FILENAME_MAX = 50
CHORUS_FILESIZE_MAX_MO = 10
CHORUS_TOTAL_FILESIZE_MAX_MO = 120
CHORUS_TOTAL_ATTACHMENTS_MAX_MO = 118
CHORUS_ALLOWED_FORMATS = [
    ".BMP",
    ".GIF",
    ".FAX",
    ".ODT",
    ".PPT",
    ".TIFF",
    ".XLS",
    ".BZ2",
    ".GZ",
    ".JPEG",
    ".P7S",
    ".RTF",
    ".TXT",
    ".XML",
    ".CSV",
    ".GZIP",
    ".JPG",
    ".PDF",
    ".SVG",
    ".XHTML",
    ".XLSX",
    ".DOC",
    ".HTM",
    ".ODP",
    ".PNG",
    ".TGZ",
    ".XLC",
    ".ZIP",
    ".DOCX",
    ".HTML",
    ".ODS",
    ".PPS",
    ".TIF",
    ".XLM",
    ".PPTX",
]


class AccountMove(models.Model):
    _inherit = "account.move"

    chorus_flow_id = fields.Many2one(
        "chorus.flow", string="Chorus Flow", readonly=True, copy=False, tracking=True
    )
    chorus_identifier = fields.Integer(
        string="Chorus Invoice Identifier", readonly=True, copy=False, tracking=True
    )
    chorus_status = fields.Char(
        string="Chorus Invoice Status", readonly=True, copy=False, tracking=True
    )
    chorus_status_date = fields.Datetime(
        string="Last Chorus Invoice Status Date", readonly=True, copy=False
    )
    chorus_attachment_ids = fields.Many2many(
        "ir.attachment",
        "account_move_chorus_ir_attachment_rel",
        string="Chorus Attachments",
        copy=False,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def _get_commitment_number(self):
        self.ensure_one()
        return self.ref

    @api.constrains("chorus_attachment_ids", "transmit_method_id")
    def _check_chorus_attachments(self):
        # https://communaute.chorus-pro.gouv.fr/pieces-jointes-dans-chorus-pro-quelques-regles-a-respecter/  # noqa: B950
        for move in self:
            if (
                move.move_type in ("out_invoice", "out_refund")
                and move.transmit_method_code == "fr-chorus"
            ):
                total_size = 0
                for attach in move.chorus_attachment_ids:
                    if len(attach.name) > CHORUS_FILENAME_MAX:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, the attachment filename is %d "
                                "caracters maximum (extension included). The "
                                "filename '%s' has %d caracters."
                            )
                            % (CHORUS_FILENAME_MAX, attach.name, len(attach.name))
                        )
                    filename, file_extension = os.path.splitext(attach.name)
                    if not file_extension:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, the attachment filenames must "
                                "have an extension. The filename '%s' doesn't "
                                "have any extension."
                            )
                            % attach.name
                        )
                    if file_extension.upper() not in CHORUS_ALLOWED_FORMATS:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, the allowed formats for the "
                                "attachments are the following: %s.\n"
                                "The attachment '%s' is not part of this list."
                            )
                            % (", ".join(CHORUS_ALLOWED_FORMATS), attach.name)
                        )
                    if not attach.file_size:
                        raise ValidationError(
                            _("The size of the attachment '%s' is 0.") % attach.name
                        )
                    total_size += attach.file_size
                    filesize_mo = round(attach.file_size / (1024 * 1024), 1)
                    if filesize_mo >= CHORUS_FILESIZE_MAX_MO:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, each attachment cannot exceed %s Mb. "
                                "The attachment '%s' weights %s Mb."
                            )
                            % (
                                CHORUS_FILESIZE_MAX_MO,
                                attach.name,
                                formatLang(self.env, filesize_mo),
                            )
                        )
                if total_size:
                    total_size_mo = round(total_size / (1024 * 1024), 1)
                    if total_size_mo > CHORUS_TOTAL_ATTACHMENTS_MAX_MO:
                        raise ValidationError(
                            _(
                                "On Chorus Pro, an invoice with its attachments "
                                "cannot exceed %s Mb, so we set a limit of %s Mb "
                                "for the attachments. The attachments have a "
                                "total size of %s Mb."
                            )
                            % (
                                CHORUS_TOTAL_FILESIZE_MAX_MO,
                                CHORUS_TOTAL_ATTACHMENTS_MAX_MO,
                                formatLang(self.env, total_size_mo),
                            )
                        )

    def action_post(self):
        """Check validity of Chorus invoices"""
        for inv in self.filtered(
            lambda x: x.move_type in ("out_invoice", "out_refund")
            and x.transmit_method_code == "fr-chorus"
        ):
            commitment_number = self._get_commitment_number()
            company_partner = inv.company_id.partner_id
            if not company_partner.siren or not company_partner.nic:
                raise UserError(
                    _("Missing SIRET on partner '%s' linked to company '%s'.")
                    % (company_partner.display_name, inv.company_id.display_name)
                )
            cpartner = inv.commercial_partner_id
            if not cpartner.siren or not cpartner.nic:
                raise UserError(
                    _(
                        "Missing SIRET on partner '%s'. "
                        "This information is required for Chorus invoices."
                    )
                    % cpartner.display_name
                )
            if (
                cpartner.fr_chorus_required in ("service", "service_and_engagement")
                and not inv.partner_id.chorus_service_ok()
            ):
                raise UserError(
                    _(
                        "Partner '%s' is configured as Service required for "
                        "Chorus, so you must select a contact as customer "
                        "for the invoice and this contact should have a name "
                        "and a Chorus service and the Chorus service must "
                        "be active."
                    )
                    % cpartner.display_name
                )
            if cpartner.fr_chorus_required in ("engagement", "service_and_engagement"):
                if commitment_number:
                    inv.chorus_invoice_check_commitment_number(commitment_number)
                else:
                    raise UserError(
                        _(
                            "Partner '%s' is configured as Engagement required for "
                            "Chorus, so the field 'Reference' of its invoices must "
                            "contain an engagement number."
                        )
                        % cpartner.display_name
                    )
            elif (
                inv.partner_id.fr_chorus_service_id
                and inv.partner_id.fr_chorus_service_id.engagement_required
            ):
                if commitment_number:
                    inv.chorus_invoice_check_commitment_number(commitment_number)
                else:
                    raise UserError(
                        _(
                            "Partner '%s' is linked to Chorus service '%s' "
                            "which is marked as 'Engagement required', so the "
                            "field 'Reference' of its invoices must "
                            "contain an engagement number."
                        )
                        % (
                            inv.partner_id.display_name,
                            inv.partner_id.fr_chorus_service_id.code,
                        )
                    )

            if cpartner.fr_chorus_required == "service_or_engagement":
                if not inv.partner_id.chorus_service_ok():
                    if not commitment_number:
                        raise UserError(
                            _(
                                "Partner '%s' is configured as "
                                "'Service or Engagement' required for Chorus but "
                                "there is no engagement number in the field "
                                "'Reference' and the customer of the "
                                "invoice is not correctly configured as a service "
                                "(should be a contact with a Chorus service "
                                "and a name)."
                            )
                            % cpartner.display_name
                        )
                    else:
                        inv.chorus_invoice_check_commitment_number()
            inv._chorus_check_payment_data()
        return super().action_post()

    def _chorus_check_payment_data(self):
        self.ensure_one()
        if self.move_type == "out_invoice":
            if not self.payment_mode_id:
                raise UserError(
                    _(
                        "Missing Payment Mode. This "
                        "information is required for Chorus."
                    )
                )
            payment_means_code = (
                self.payment_mode_id.payment_method_id.unece_code or "30"
            )
            partner_bank_id = self.partner_bank_id or (
                self.payment_mode_id.bank_account_link == "fixed"
                and self.payment_mode_id.fixed_journal_id.bank_account_id
            )
            if payment_means_code in CREDIT_TRF_CODES:
                if not partner_bank_id:
                    raise UserError(
                        _(
                            "Missing bank account information for payment. "
                            "For that, you have two options: either the "
                            "payment mode of the invoice should have "
                            "'Link to Bank Account' = "
                            "'fixed' and the related bank journal should have "
                            "a 'Bank Account' set, or the field "
                            "'Bank Account' should be set on the customer "
                            "invoice."
                        )
                    )
                if partner_bank_id.acc_type != "iban":
                    raise UserError(
                        _(
                            "Chorus only accepts IBAN. But the bank account "
                            "'%s' is not an IBAN."
                        )
                        % partner_bank_id.acc_number
                    )
        elif self.move_type == "out_refund":
            if self.payment_mode_id:
                raise UserError(
                    _(
                        "The Payment Mode must be empty "
                        "for customer refunds sent to Chorus."
                    )
                )

    def chorus_get_invoice(self, chorus_invoice_format):
        self.ensure_one()
        return False

    def prepare_chorus_deposer_flux_payload(self):
        if not self[0].company_id.fr_chorus_invoice_format:
            raise UserError(
                _(
                    "The Chorus Invoice Format is not configured on the "
                    "Accounting Configuration page of company '%s'"
                )
                % self[0].company_id.display_name
            )
        chorus_invoice_format = self[0].company_id.fr_chorus_invoice_format
        short_format = chorus_invoice_format[4:]
        file_extension = chorus_invoice_format[:3]
        syntaxe_flux = self.env["chorus.flow"].syntax_odoo2chorus()[
            chorus_invoice_format
        ]
        if len(self) == 1:
            chorus_file_content = self.chorus_get_invoice(chorus_invoice_format)
            filename = "{}_chorus_facture_{}.{}".format(
                short_format,
                self.name.replace("/", "-"),
                file_extension,
            )
        else:
            filename = "%s_chorus_lot_factures.tar.gz" % short_format
            tarfileobj = BytesIO()
            with tarfile.open(fileobj=tarfileobj, mode="w:gz") as tar:
                for inv in self:
                    inv_file_data = inv.chorus_get_invoice(chorus_invoice_format)
                    invfileio = BytesIO(inv_file_data)
                    invfilename = "{}_chorus_facture_{}.{}".format(
                        short_format,
                        inv.name.replace("/", "-"),
                        file_extension,
                    )
                    tarinfo = tarfile.TarInfo(name=invfilename)
                    tarinfo.size = len(inv_file_data)
                    tarinfo.mtime = int(time.time())
                    tar.addfile(tarinfo=tarinfo, fileobj=invfileio)
                tar.close()
            tarfileobj.seek(0)
            chorus_file_content = tarfileobj.read()
        payload = {
            "fichierFlux": base64.b64encode(chorus_file_content).decode("ascii"),
            "nomFichier": filename,
            "syntaxeFlux": syntaxe_flux,
            "avecSignature": False,
        }
        return payload

    def chorus_api_consulter_historique(self, api_params, session=None):
        url_path = "factures/v1/consulter/historique"
        payload = {
            "idFacture": self.chorus_identifier,
        }
        answer, session = self.env["res.company"].chorus_post(
            api_params, url_path, payload, session=session
        )
        res = False
        if (
            answer.get("idFacture")
            and answer["idFacture"] == self.chorus_identifier
            and answer.get("statutCourantCode")
        ):
            res = answer["statutCourantCode"]
        return (res, session)

    def chorus_update_invoice_status(self):
        """Called by a button on the invoice or by cron"""
        logger.info("Start to update chorus invoice status")
        company2api = {}
        raise_if_ko = self._context.get("chorus_raise_if_ko", True)
        invoices = []
        for inv in self:
            if not inv.chorus_identifier:
                if raise_if_ko:
                    raise UserError(
                        _("Missing Chorus Invoice Identifier on invoice '%s'")
                        % inv.display_name
                    )
                logger.warning(
                    "Skipping invoice %s: missing chorus invoice identifier", inv.name
                )
                continue
            company = inv.company_id
            if company not in company2api:
                api_params = company.chorus_get_api_params(raise_if_ko=raise_if_ko)
                if not api_params:
                    continue
                company2api[company] = api_params
            invoices.append(inv)
        session = None
        for invoice in invoices:
            api_params = company2api[invoice.company_id]
            inv_status, session = invoice.chorus_api_consulter_historique(
                api_params, session
            )
            if inv_status:
                invoice.write(
                    {
                        "chorus_status": inv_status,
                        "chorus_status_date": fields.Datetime.now(),
                    }
                )
        logger.info("End of the update of chorus invoice status")

    def chorus_invoice_check_commitment_number(
        self, commitment_number, raise_if_not_found=True
    ):
        self.ensure_one()
        res = self.chorus_check_commitment_number(
            self.company_id, commitment_number, raise_if_not_found=raise_if_not_found
        )
        if res is True:
            self.message_post(
                body=_("Engagement juridique <b>%s</b> checked via Chorus Pro API.")
                % commitment_number
            )
        return res

    # api.model because this method is called from invoice
    # but also from sale.order
    @api.model
    def chorus_check_commitment_number(
        self, company, order_ref, raise_if_not_found=True
    ):
        if not order_ref:
            raise UserError(_("Missing commitment number."))
        if not company.fr_chorus_check_commitment_number:
            logger.info(
                "Commitment number check not enabled on company %s",
                company.display_name,
            )
            return
        if not self.env.user.has_group("l10n_fr_chorus_account.group_chorus_api"):
            return
        if not company.partner_id.fr_chorus_identifier:
            company.partner_id.sudo().with_context(
                get_company_identifier=True
            ).fr_chorus_identifier_get()
        company_identifier = company.partner_id.fr_chorus_identifier
        order_ref = order_ref.strip()
        if len(order_ref) > 50:
            raise UserError(
                _(
                    "The engagement juridique '%s' is %d caracters long. "
                    "The maximum is 50. Please update the customer order "
                    "reference."
                )
                % (order_ref, len(order_ref))
            )
        api_params = company.chorus_get_api_params()
        return self.chorus_api_check_commitment_number(
            api_params,
            company_identifier,
            order_ref,
            raise_if_not_found=raise_if_not_found,
        )

    @api.model
    def chorus_api_check_commitment_number(
        self,
        api_params,
        company_identifier,
        order_ref,
        session=None,
        raise_if_not_found=True,
    ):
        assert order_ref
        url_path = "engagementsJuridiques/v1/rechercher"
        payload = {
            "structureReceptriceEngagementJuridique": str(company_identifier),
            "numeroEngagementJuridique": order_ref,
            "etatCourantEngagementJuridique": "COMMANDE",
        }
        answer, session = self.env["res.company"].chorus_post(
            api_params, url_path, payload, session=session
        )
        if answer.get("listeEngagementJuridique"):
            if len(answer["listeEngagementJuridique"]) == 1:
                return True
            elif len(answer["listeEngagementJuridique"]) > 1:
                logger.warning("Several engagements juridiques... strange!")
                return True
        elif raise_if_not_found:
            raise UserError(
                _(
                    "Commitment number '%s' not found in Chorus Pro. "
                    "Please check the customer order reference carefully."
                )
                % order_ref
            )
        logger.warning("Commitment number %s not found in Chorus Pro.", order_ref)
        return False
