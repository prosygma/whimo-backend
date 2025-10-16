import django.contrib.auth.validators
import django.contrib.postgres.indexes
import django.db.models.deletion
import django.utils.timezone
import simple_history.models
import uuid
import whimo.common.encoders
import whimo.db.enums.notifications
import whimo.db.models.users
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommodityGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                ("name", models.CharField(help_text="Name of the commodity group", max_length=50)),
            ],
            options={
                "verbose_name": "Commodity Group",
                "verbose_name_plural": "Commodity Groups",
                "db_table": "commodity_groups",
                "ordering": ("name",),
            },
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
                (
                    "is_deleted",
                    models.BooleanField(default=False, help_text="Indicates whether this user has been soft deleted"),
                ),
            ],
            options={
                "verbose_name": "User",
                "verbose_name_plural": "Users",
                "db_table": "users",
                "ordering": ("-username",),
            },
            managers=[
                ("objects", whimo.db.models.users.CustomUserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Commodity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                ("code", models.CharField(help_text="Commodity code", max_length=20, unique=True)),
                ("name", models.CharField(help_text="Name of the commodity", max_length=255)),
                ("unit", models.CharField(help_text="Unit of measurement", max_length=10)),
                (
                    "group",
                    models.ForeignKey(
                        help_text="Commodity group",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="commodities",
                        to="db.commoditygroup",
                    ),
                ),
            ],
            options={
                "verbose_name": "Commodity",
                "verbose_name_plural": "Commodities",
                "db_table": "commodities",
                "ordering": ("code",),
            },
        ),
        migrations.CreateModel(
            name="Gadget",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("phone", "PHONE"), ("email", "EMAIL")],
                        help_text="Type of contact method (phone or email)",
                        max_length=10,
                    ),
                ),
                (
                    "identifier",
                    models.CharField(
                        help_text="Contact identifier (e.g. email address or phone number)", max_length=255, unique=True
                    ),
                ),
                (
                    "is_verified",
                    models.BooleanField(
                        default=False, help_text="Indicates whether this contact method has been verified by the user"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="The user this gadget belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gadgets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Gadget",
                "verbose_name_plural": "Gadgets",
                "db_table": "gadgets",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="HistoricalCommodity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("code", models.CharField(db_index=True, help_text="Commodity code", max_length=20)),
                ("name", models.CharField(help_text="Name of the commodity", max_length=255)),
                ("unit", models.CharField(help_text="Unit of measurement", max_length=10)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Commodity group",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.commoditygroup",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Commodity",
                "verbose_name_plural": "historical Commodities",
                "db_table": "commodities_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalCommodityGroup",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("name", models.CharField(help_text="Name of the commodity group", max_length=50)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Commodity Group",
                "verbose_name_plural": "historical Commodity Groups",
                "db_table": "commodity_groups_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalGadget",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("phone", "PHONE"), ("email", "EMAIL")],
                        help_text="Type of contact method (phone or email)",
                        max_length=10,
                    ),
                ),
                (
                    "identifier",
                    models.CharField(
                        db_index=True,
                        help_text="Contact identifier (e.g. email address or phone number)",
                        max_length=255,
                    ),
                ),
                (
                    "is_verified",
                    models.BooleanField(
                        default=False, help_text="Indicates whether this contact method has been verified by the user"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="The user this gadget belongs to",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Gadget",
                "verbose_name_plural": "historical Gadgets",
                "db_table": "gadgets_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalBalance",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("volume", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Balance commodity",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.commodity",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Balance user",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Balance",
                "verbose_name_plural": "historical Balances",
                "db_table": "balances_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Balance",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                ("volume", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                (
                    "commodity",
                    models.ForeignKey(
                        # default=None,
                        # help_text="Balance commodity",
                        # on_delete=django.db.models.deletion.PROTECT,
                        # to="db.commodity",
                        help_text="Balance commodity",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="db.commodity",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="Balance user",
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Balance",
                "verbose_name_plural": "Balances",
                "db_table": "balances",
            },
        ),
        migrations.CreateModel(
            name="HistoricalUser",
            fields=[
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        db_index=True,
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "is_deleted",
                    models.BooleanField(default=False, help_text="Indicates whether this user has been soft deleted"),
                ),
            ],
            options={
                "verbose_name": "historical User",
                "verbose_name_plural": "historical Users",
                "db_table": "users_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalTransaction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("producer", "PRODUCER"), ("downstream", "DOWNSTREAM")],
                        help_text="Type of transaction",
                        max_length=20,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        choices=[("qr", "QR"), ("manual", "MANUAL"), ("file", "FILE"), ("gps", "GPS")],
                        help_text="Source of location geodata",
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "PENDING"),
                            ("accepted", "ACCEPTED"),
                            ("rejected", "REJECTED"),
                            ("no_response", "NO_RESPONSE"),
                        ],
                        default=whimo.db.enums.transactions.TransactionStatus["PENDING"],
                        help_text="Status of the transaction",
                        max_length=20,
                    ),
                ),
                (
                    "latitude",
                    models.DecimalField(
                        blank=True, decimal_places=6, help_text="Latitude coordinate", max_digits=9, null=True
                    ),
                ),
                (
                    "longitude",
                    models.DecimalField(
                        blank=True, decimal_places=6, help_text="Longitude coordinate", max_digits=9, null=True
                    ),
                ),
                ("volume", models.DecimalField(decimal_places=2, help_text="Volume of commodities", max_digits=10)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "buyer",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Buyer in this transaction",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Commodity being traded",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.commodity",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Seller in this transaction",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="User who created this transaction",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "traceability",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("full", "FULL"),
                            ("conditional", "CONDITIONAL"),
                            ("partial", "PARTIAL"),
                            ("incomplete", "INCOMPLETE"),
                        ],
                        help_text="Traceability status of the transaction",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "is_buying_from_farmer",
                    models.BooleanField(
                        default=False, help_text="Whether this transaction is buying from a farmer directly"
                    ),
                ),
                (
                    "is_automatic",
                    models.BooleanField(default=False, help_text="Whether this transaction was created automatically"),
                ),
                ("expires_at", models.DateTimeField(blank=True, help_text="When this transaction expires", null=True)),
            ],
            options={
                "verbose_name": "historical Transaction",
                "verbose_name_plural": "historical Transactions",
                "db_table": "transactions_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("producer", "PRODUCER"), ("downstream", "DOWNSTREAM")],
                        help_text="Type of transaction",
                        max_length=20,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        choices=[("qr", "QR"), ("manual", "MANUAL"), ("file", "FILE"), ("gps", "GPS")],
                        help_text="Source of location geodata",
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "PENDING"),
                            ("accepted", "ACCEPTED"),
                            ("rejected", "REJECTED"),
                            ("no_response", "NO_RESPONSE"),
                        ],
                        default=whimo.db.enums.transactions.TransactionStatus["PENDING"],
                        help_text="Status of the transaction",
                        max_length=20,
                    ),
                ),
                (
                    "latitude",
                    models.DecimalField(
                        blank=True, decimal_places=6, help_text="Latitude coordinate", max_digits=9, null=True
                    ),
                ),
                (
                    "longitude",
                    models.DecimalField(
                        blank=True, decimal_places=6, help_text="Longitude coordinate", max_digits=9, null=True
                    ),
                ),
                ("volume", models.DecimalField(decimal_places=2, help_text="Volume of commodities", max_digits=10)),
                (
                    "buyer",
                    models.ForeignKey(
                        blank=True,
                        help_text="Buyer in this transaction",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bought",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        help_text="Commodity being traded",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transactions",
                        to="db.commodity",
                    ),
                ),
                (
                    "seller",
                    models.ForeignKey(
                        blank=True,
                        help_text="Seller in this transaction",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sold",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="User who created this transaction",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_transactions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "traceability",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("full", "FULL"),
                            ("conditional", "CONDITIONAL"),
                            ("partial", "PARTIAL"),
                            ("incomplete", "INCOMPLETE"),
                        ],
                        help_text="Traceability status of the transaction",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "is_buying_from_farmer",
                    models.BooleanField(
                        default=False, help_text="Whether this transaction is buying from a farmer directly"
                    ),
                ),
                (
                    "is_automatic",
                    models.BooleanField(default=False, help_text="Whether this transaction was created automatically"),
                ),
                ("expires_at", models.DateTimeField(blank=True, help_text="When this transaction expires", null=True)),
            ],
            options={
                "verbose_name": "Transaction",
                "verbose_name_plural": "Transactions",
                "db_table": "transactions",
                "ordering": ("-created_at", "-commodity_id"),
            },
        ),
        migrations.CreateModel(
            name="HistoricalNotification",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "data",
                    models.JSONField(
                        blank=True,
                        encoder=whimo.common.encoders.PrettyJSONEncoder,
                        help_text="Notification data",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "PENDING"), ("read", "READ")],
                        default=whimo.db.enums.notifications.NotificationStatus["PENDING"],
                        help_text="Status of the notification",
                        max_length=30,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("transaction_pending", "TRANSACTION_PENDING"),
                            ("transaction_accepted", "TRANSACTION_ACCEPTED"),
                            ("transaction_rejected", "TRANSACTION_REJECTED"),
                            ("transaction_expired", "TRANSACTION_EXPIRED"),
                            ("geodata_missing", "GEODATA_MISSING"),
                            ("geodata_updated", "GEODATA_UPDATED"),
                        ],
                        help_text="Type of notification",
                        max_length=20,
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="User who created this notification",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "received_by",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="User who received this notification",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Notification",
                "verbose_name_plural": "historical Notifications",
                "db_table": "notifications_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Notification",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "data",
                    models.JSONField(
                        blank=True,
                        encoder=whimo.common.encoders.PrettyJSONEncoder,
                        help_text="Notification data",
                        null=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "PENDING"), ("read", "READ")],
                        default=whimo.db.enums.notifications.NotificationStatus["PENDING"],
                        help_text="Status of the notification",
                        max_length=30,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("transaction_pending", "TRANSACTION_PENDING"),
                            ("transaction_accepted", "TRANSACTION_ACCEPTED"),
                            ("transaction_rejected", "TRANSACTION_REJECTED"),
                            ("transaction_expired", "TRANSACTION_EXPIRED"),
                            ("geodata_missing", "GEODATA_MISSING"),
                            ("geodata_updated", "GEODATA_UPDATED"),
                        ],
                        help_text="Type of notification",
                        max_length=20,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created this notification",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "received_by",
                    models.ForeignKey(
                        help_text="User who received this notification",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="received_notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Notification",
                "verbose_name_plural": "Notifications",
                "db_table": "notifications",
                "ordering": ("created_at",),
            },
        ),
        migrations.CreateModel(
            name="HistoricalNotificationSettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("transaction_pending", "TRANSACTION_PENDING"),
                            ("transaction_accepted", "TRANSACTION_ACCEPTED"),
                            ("transaction_rejected", "TRANSACTION_REJECTED"),
                            ("transaction_expired", "TRANSACTION_EXPIRED"),
                            ("geodata_missing", "GEODATA_MISSING"),
                            ("geodata_updated", "GEODATA_UPDATED"),
                        ],
                        help_text="Type of notification",
                        max_length=20,
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=True, help_text="Indicates whether notifications of this type are enabled"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="User who owns this notification settings",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Notification Settings",
                "verbose_name_plural": "historical Notification Settings",
                "db_table": "notification_settings_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="NotificationSettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("transaction_pending", "TRANSACTION_PENDING"),
                            ("transaction_accepted", "TRANSACTION_ACCEPTED"),
                            ("transaction_rejected", "TRANSACTION_REJECTED"),
                            ("transaction_expired", "TRANSACTION_EXPIRED"),
                            ("geodata_missing", "GEODATA_MISSING"),
                            ("geodata_updated", "GEODATA_UPDATED"),
                        ],
                        help_text="Type of notification",
                        max_length=20,
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=True, help_text="Indicates whether notifications of this type are enabled"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User who owns this notification settings",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notification_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Notification Settings",
                "verbose_name_plural": "Notification Settings",
                "db_table": "notification_settings",
                "ordering": ("user", "type"),
                "unique_together": {("user", "type")},
            },
        ),
        migrations.RenameField(
            model_name="historicaltransaction",
            old_name="latitude",
            new_name="transaction_latitude",
        ),
        migrations.RenameField(
            model_name="historicaltransaction",
            old_name="longitude",
            new_name="transaction_longitude",
        ),
        migrations.RenameField(
            model_name="transaction",
            old_name="latitude",
            new_name="transaction_latitude",
        ),
        migrations.RenameField(
            model_name="transaction",
            old_name="longitude",
            new_name="transaction_longitude",
        ),
        migrations.AddField(
            model_name="historicaltransaction",
            name="farm_latitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Farm latitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AddField(
            model_name="historicaltransaction",
            name="farm_longitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Farm longitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="farm_latitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Farm latitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="farm_longitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Farm longitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AlterField(
            model_name="historicaltransaction",
            name="transaction_latitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Transaction latitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AlterField(
            model_name="historicaltransaction",
            name="transaction_longitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Transaction longitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="transaction_latitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Transaction latitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="transaction_longitude",
            field=models.DecimalField(
                blank=True, decimal_places=6, help_text="Transaction longitude coordinate", max_digits=9, null=True
            ),
        ),
        migrations.AddField(
            model_name="commodity",
            name="name_variants",
            field=models.JSONField(blank=True, default=list, help_text="Alternative name variations and translations"),
        ),
        migrations.AddField(
            model_name="commoditygroup",
            name="name_variants",
            field=models.JSONField(blank=True, default=list, help_text="Alternative name variations and translations"),
        ),
        migrations.AddIndex(
            model_name="commodity",
            index=django.contrib.postgres.indexes.GinIndex(fields=["name_variants"], name="db_comm_name_vars_gin_idx"),
        ),
        migrations.AddIndex(
            model_name="commoditygroup",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["name_variants"], name="db_commgrp_name_vars_gin_idx"
            ),
        ),
        migrations.CreateModel(
            name="Season",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                ("name", models.CharField(help_text="Name of the season", max_length=255)),
                ("description", models.TextField(blank=True, help_text="Description of the season", null=True)),
                ("start_date", models.DateField(blank=True, help_text="Start date of the season", null=True)),
                ("end_date", models.DateField(blank=True, help_text="End date of the season", null=True)),
            ],
            options={
                "verbose_name": "Season",
                "verbose_name_plural": "Seasons",
                "db_table": "seasons",
                "ordering": ("-start_date",),
            },
        ),
        migrations.CreateModel(
            name="HistoricalSeason",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("name", models.CharField(help_text="Name of the season", max_length=255)),
                ("description", models.TextField(blank=True, help_text="Description of the season", null=True)),
                ("start_date", models.DateField(blank=True, help_text="Start date of the season", null=True)),
                ("end_date", models.DateField(blank=True, help_text="End date of the season", null=True)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Season",
                "verbose_name_plural": "historical Seasons",
                "db_table": "seasons_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalSeasonCommodity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Commodity",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.commodity",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "season",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Season",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.season",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Season Commodity",
                "verbose_name_plural": "historical Season Commodities",
                "db_table": "season_commodities_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name="historicaltransaction",
            name="season",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Season this transaction belongs to",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="db.season",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="season",
            field=models.ForeignKey(
                blank=True,
                help_text="Season this transaction belongs to",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="transactions",
                to="db.season",
            ),
        ),
        migrations.CreateModel(
            name="SeasonCommodity",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        help_text="Commodity",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="season_commodities",
                        to="db.commodity",
                    ),
                ),
                (
                    "season",
                    models.ForeignKey(
                        help_text="Season",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="season_commodities",
                        to="db.season",
                    ),
                ),
            ],
            options={
                "verbose_name": "Season Commodity",
                "verbose_name_plural": "Season Commodities",
                "db_table": "season_commodities",
                "ordering": ("season", "commodity"),
                "unique_together": {("season", "commodity")},
            },
        ),
        migrations.AddField(
            model_name="season",
            name="commodities",
            field=models.ManyToManyField(
                help_text="Commodities participating in this season",
                related_name="seasons",
                through="db.SeasonCommodity",
                to="db.commodity",
            ),
        ),
        migrations.CreateModel(
            name="ConversionRecipe",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                ("name", models.CharField(help_text="Name or description of this conversion recipe", max_length=255)),
            ],
            options={
                "verbose_name": "Conversion Recipe",
                "verbose_name_plural": "Conversion Recipes",
                "db_table": "conversion_recipes",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="HistoricalConversionInput",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=6, help_text="Quantity of this commodity required as input", max_digits=15
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Input commodity",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.commodity",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Conversion recipe",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.conversionrecipe",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Conversion Input",
                "verbose_name_plural": "historical Conversion Inputs",
                "db_table": "conversion_inputs_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalConversionOutput",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=6, help_text="Quantity of this commodity produced as output", max_digits=15
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Output commodity",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.commodity",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Conversion recipe",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="db.conversionrecipe",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Conversion Output",
                "verbose_name_plural": "historical Conversion Outputs",
                "db_table": "conversion_outputs_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalConversionRecipe",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                ("name", models.CharField(help_text="Name or description of this conversion recipe", max_length=255)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Conversion Recipe",
                "verbose_name_plural": "historical Conversion Recipes",
                "db_table": "conversion_recipes_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="ConversionOutput",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=6, help_text="Quantity of this commodity produced as output", max_digits=15
                    ),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        help_text="Output commodity",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversion_outputs",
                        to="db.commodity",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        help_text="Conversion recipe",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outputs",
                        to="db.conversionrecipe",
                    ),
                ),
            ],
            options={
                "verbose_name": "Conversion Output",
                "verbose_name_plural": "Conversion Outputs",
                "db_table": "conversion_outputs",
                "ordering": ("recipe", "commodity"),
                "unique_together": {("recipe", "commodity")},
            },
        ),
        migrations.CreateModel(
            name="ConversionInput",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        decimal_places=6, help_text="Quantity of this commodity required as input", max_digits=15
                    ),
                ),
                (
                    "commodity",
                    models.ForeignKey(
                        help_text="Input commodity",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversion_inputs",
                        to="db.commodity",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        help_text="Conversion recipe",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inputs",
                        to="db.conversionrecipe",
                    ),
                ),
            ],
            options={
                "verbose_name": "Conversion Input",
                "verbose_name_plural": "Conversion Inputs",
                "db_table": "conversion_inputs",
                "ordering": ("recipe", "commodity"),
                "unique_together": {("recipe", "commodity")},
            },
        ),
        migrations.AlterField(
            model_name="historicaltransaction",
            name="type",
            field=models.CharField(
                choices=[("producer", "PRODUCER"), ("downstream", "DOWNSTREAM"), ("conversion", "CONVERSION")],
                help_text="Type of transaction",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="type",
            field=models.CharField(
                choices=[("producer", "PRODUCER"), ("downstream", "DOWNSTREAM"), ("conversion", "CONVERSION")],
                help_text="Type of transaction",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="historicaltransaction",
            name="group_id",
            field=models.UUIDField(blank=True, help_text="Transaction group id", null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="group_id",
            field=models.UUIDField(blank=True, help_text="Transaction group id", null=True),
        ),
    ]
