from whimo.contrib.admin.balances import BalanceAdmin
from whimo.contrib.admin.celery import (
    ClockedScheduleAdmin,
    CrontabScheduleAdmin,
    IntervalScheduleAdmin,
    PeriodicTaskAdmin,
    SolarScheduleAdmin,
)
from whimo.contrib.admin.commodities import CommodityAdmin, CommodityGroupAdmin
from whimo.contrib.admin.conversions import ConversionRecipeAdmin
from whimo.contrib.admin.harvest_seasons import HarvestSeasonAdmin
from whimo.contrib.admin.notifications import NotificationAdmin
from whimo.contrib.admin.transactions import TransactionAdmin
from whimo.contrib.admin.users import GadgetAdmin, UserAdmin
from whimo.contrib.admin.whatsapp import WhatsAppSettingsAdmin

__all__ = (
    "BalanceAdmin",
    "ClockedScheduleAdmin",
    "CommodityAdmin",
    "CommodityGroupAdmin",
    "ConversionRecipeAdmin",
    "CrontabScheduleAdmin",
    "GadgetAdmin",
    "HarvestSeasonAdmin",
    "IntervalScheduleAdmin",
    "NotificationAdmin",
    "PeriodicTaskAdmin",
    "SolarScheduleAdmin",
    "TransactionAdmin",
    "UserAdmin",
    "WhatsAppSettingsAdmin",
)
