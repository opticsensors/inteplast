"""Shared feature/piece membership for the Features and Metrology selectors."""

from sqlalchemy.sql.selectable import Subquery
from sqlmodel import col, select

from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic
from app.models import FeatureAsset, FeaturePartLink


def feature_membership() -> Subquery:
    return (
        select(FeaturePartLink.part_id, FeaturePartLink.feature_id)
        .union(
            select(FeatureAsset.part_id, FeatureAsset.feature_id).where(
                col(FeatureAsset.part_id).is_not(None)
            ),
            select(
                PartCharacteristic.part_id, FeatureCharacteristicLink.feature_id
            ).join(FeatureCharacteristicLink),
        )
        .subquery()
    )
