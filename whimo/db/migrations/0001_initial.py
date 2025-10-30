import uuid

import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
import simple_history.models
from django.conf import settings
from django.db import migrations, models

import whimo.db.enums.transactions
import whimo.db.models.users


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
                        help_text="Commodity group", on_delete=django.db.models.deletion.PROTECT, to="db.commoditygroup"
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
            ],
            options={
                "verbose_name": "Transaction",
                "verbose_name_plural": "Transactions",
                "db_table": "transactions",
                "ordering": ("-created_at", "-commodity_id"),
            },
        ),
    ]
