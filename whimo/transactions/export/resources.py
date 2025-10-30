from import_export import fields, resources

from whimo.db.models import Transaction


class TransactionUserResource(resources.ModelResource):
    transaction_id = fields.Field(attribute="id", column_name="Transaction ID")
    transaction_created_at = fields.Field(attribute="created_at", column_name="Transaction Created At")
    transaction_type = fields.Field(attribute="type", column_name="Transaction Type")
    transaction_status = fields.Field(attribute="status", column_name="Transaction Status")
    transaction_traceability = fields.Field(attribute="traceability", column_name="Transaction Traceability")
    location = fields.Field(attribute="location", column_name="Location Type")
    transaction_latitude = fields.Field(attribute="transaction_latitude", column_name="Transaction Latitude")
    transaction_longitude = fields.Field(attribute="transaction_longitude", column_name="Transaction Longitude")
    farm_latitude = fields.Field(attribute="farm_latitude", column_name="Farm Latitude")
    farm_longitude = fields.Field(attribute="farm_longitude", column_name="Farm Longitude")
    volume = fields.Field(attribute="volume", column_name="Volume")
    is_automatic = fields.Field(attribute="is_automatic", column_name="Is Automatic")
    created_by_role = fields.Field(column_name="Created By Role")
    commodity_id = fields.Field(attribute="commodity__id", column_name="Commodity ID")
    commodity_code = fields.Field(attribute="commodity__code", column_name="Commodity Code")
    commodity_name = fields.Field(attribute="commodity__name", column_name="Commodity Name")
    commodity_unit = fields.Field(attribute="commodity__unit", column_name="Commodity Unit")
    commodity_group = fields.Field(attribute="commodity__group__name", column_name="Commodity Group")
    seller_id = fields.Field(attribute="seller__id", column_name="Seller ID")
    seller_created_at = fields.Field(attribute="seller__created_at", column_name="Seller Created At")
    buyer_id = fields.Field(attribute="buyer__id", column_name="Buyer ID")
    buyer_created_at = fields.Field(attribute="buyer__created_at", column_name="Buyer Created At")

    class Meta:
        model = Transaction
        fields = (
            "transaction_id",
            "transaction_created_at",
            "transaction_type",
            "transaction_status",
            "transaction_traceability",
            "location",
            "transaction_latitude",
            "transaction_longitude",
            "farm_latitude",
            "farm_longitude",
            "volume",
            "is_automatic",
            "created_by_role",
            "commodity_id",
            "commodity_code",
            "commodity_name",
            "commodity_unit",
            "commodity_group",
            "seller_id",
            "seller_created_at",
            "buyer_id",
            "buyer_created_at",
        )
        export_order = fields

    def dehydrate_created_by_role(self, transaction: Transaction) -> str:
        if transaction.created_by_id == transaction.seller_id:
            return "seller"
        if transaction.created_by_id == transaction.buyer_id:
            return "buyer"
        return "other"


class TransactionAdminResource(resources.ModelResource):
    transaction_id = fields.Field(attribute="id", column_name="Transaction ID")
    transaction_created_at = fields.Field(attribute="created_at", column_name="Transaction Created At")
    transaction_type = fields.Field(attribute="type", column_name="Transaction Type")
    transaction_status = fields.Field(attribute="status", column_name="Transaction Status")
    transaction_traceability = fields.Field(attribute="traceability", column_name="Transaction Traceability")
    location = fields.Field(attribute="location", column_name="Location Type")
    transaction_latitude = fields.Field(attribute="transaction_latitude", column_name="Transaction Latitude")
    transaction_longitude = fields.Field(attribute="transaction_longitude", column_name="Transaction Longitude")
    farm_latitude = fields.Field(attribute="farm_latitude", column_name="Farm Latitude")
    farm_longitude = fields.Field(attribute="farm_longitude", column_name="Farm Longitude")
    volume = fields.Field(attribute="volume", column_name="Volume")
    is_automatic = fields.Field(attribute="is_automatic", column_name="Is Automatic")
    created_by_role = fields.Field(column_name="Created By Role")
    commodity_id = fields.Field(attribute="commodity__id", column_name="Commodity ID")
    commodity_code = fields.Field(attribute="commodity__code", column_name="Commodity Code")
    commodity_name = fields.Field(attribute="commodity__name", column_name="Commodity Name")
    commodity_unit = fields.Field(attribute="commodity__unit", column_name="Commodity Unit")
    commodity_group = fields.Field(attribute="commodity__group__name", column_name="Commodity Group")
    seller_id = fields.Field(attribute="seller__id", column_name="Seller ID")
    seller_created_at = fields.Field(attribute="seller__created_at", column_name="Seller Created At")
    seller_email = fields.Field(column_name="Seller Email")
    seller_phone = fields.Field(column_name="Seller Phone")
    buyer_id = fields.Field(attribute="buyer__id", column_name="Buyer ID")
    buyer_created_at = fields.Field(attribute="buyer__created_at", column_name="Buyer Created At")
    buyer_email = fields.Field(column_name="Buyer Email")
    buyer_phone = fields.Field(column_name="Buyer Phone")

    class Meta:
        model = Transaction
        fields = (
            "transaction_id",
            "transaction_created_at",
            "transaction_type",
            "transaction_status",
            "transaction_traceability",
            "location",
            "transaction_latitude",
            "transaction_longitude",
            "farm_latitude",
            "farm_longitude",
            "volume",
            "is_automatic",
            "created_by_role",
            "commodity_id",
            "commodity_code",
            "commodity_name",
            "commodity_unit",
            "commodity_group",
            "seller_id",
            "seller_created_at",
            "seller_email",
            "seller_phone",
            "buyer_id",
            "buyer_created_at",
            "buyer_email",
            "buyer_phone",
        )
        export_order = fields

    def dehydrate_seller_email(self, transaction: Transaction) -> str:
        if transaction.seller:
            email_gadgets = transaction.seller.gadgets.filter(type="EMAIL", is_verified=True)
            email_gadget = email_gadgets.first()
            return email_gadget.identifier if email_gadget else ""
        return ""

    def dehydrate_seller_phone(self, transaction: Transaction) -> str:
        if transaction.seller:
            phone_gadgets = transaction.seller.gadgets.filter(type="PHONE", is_verified=True)
            phone_gadget = phone_gadgets.first()
            return phone_gadget.identifier if phone_gadget else ""
        return ""

    def dehydrate_buyer_email(self, transaction: Transaction) -> str:
        if transaction.buyer:
            email_gadgets = transaction.buyer.gadgets.filter(type="EMAIL", is_verified=True)
            email_gadget = email_gadgets.first()
            return email_gadget.identifier if email_gadget else ""
        return ""

    def dehydrate_buyer_phone(self, transaction: Transaction) -> str:
        if transaction.buyer:
            phone_gadgets = transaction.buyer.gadgets.filter(type="PHONE", is_verified=True)
            phone_gadget = phone_gadgets.first()
            return phone_gadget.identifier if phone_gadget else ""
        return ""

    def dehydrate_created_by_role(self, transaction: Transaction) -> str:
        if transaction.created_by_id == transaction.seller_id:
            return "seller"
        if transaction.created_by_id == transaction.buyer_id:
            return "buyer"
        return "other"
