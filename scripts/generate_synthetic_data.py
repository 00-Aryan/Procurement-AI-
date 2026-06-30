import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sqlalchemy import text

# Ensure root of project is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infra.database import (
    Base,
    engine,
    AsyncSessionFactory,
    tenant_session,
    Tenant,
    Node,
    Flow,
)


def generate_jharkhand_gstin() -> str:
    """Generates a random valid GSTIN with state code 20 (Jharkhand)."""
    pan_letters = "".join(np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=5))
    pan_numbers = "".join(np.random.choice(list("0123456789"), size=4))
    entity_indicator = np.random.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    entity_number = np.random.choice(list("123456789"))
    check_digit = np.random.choice(list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    return f"20{pan_letters}{pan_numbers}{entity_indicator}{entity_number}Z{check_digit}"


def generate_dates(num_records: int) -> list[datetime]:
    """Generates dates uniformly within Q1 and Q2 2026 range boundaries."""
    start_date = pd.to_datetime("2026-01-01T00:00:00Z")
    end_date = pd.to_datetime("2026-06-30T23:59:59Z")
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    random_ts = np.random.randint(start_ts, end_ts, size=num_records)
    return [datetime.fromtimestamp(ts, tz=timezone.utc) for ts in random_ts]


async def init_db():
    """Creates the database schema if it doesn't already exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def main():
    print("Initializing database schema...")
    await init_db()

    tenant_name = "Central Coalfields Limited"
    print(f"Ensuring tenant '{tenant_name}' exists...")
    
    tenant_id = None
    # 1. Global Session to manage Tenant structure
    async with AsyncSessionFactory() as session:
        # Check if tenant exists
        result = await session.execute(
            text("SELECT id FROM tenants WHERE name = :name"),
            {"name": tenant_name}
        )
        row = result.fetchone()
        if row:
            tenant_id = row[0]
            print(f"Found existing tenant: {tenant_id}")
        else:
            # Create new tenant
            new_tenant = Tenant(name=tenant_name)
            session.add(new_tenant)
            await session.commit()
            tenant_id = new_tenant.id
            print(f"Created new tenant: {tenant_id}")

    # 2. Tenant Session to seed multi-tenant isolated tables
    print("Starting transaction to seed nodes and flows under tenant context...")
    async with tenant_session(tenant_id) as session:
        # Clear existing nodes/flows for clean seed
        await session.execute(text("DELETE FROM flows"))
        await session.execute(text("DELETE FROM nodes"))
        
        # Pre-generate dates
        total_records_needed = 1 + 500 + 30 + 50 + 30 + 500
        dates_pool = generate_dates(total_records_needed)
        date_idx = 0

        # Create Central CCL Buyer Node
        buyer_node = Node(
            tenant_id=tenant_id,
            name="CCL Ranchi/Khalari Headquarters",
            type="buyer",
            industry_attributes={
                "location": "Ranchi/Khalari",
                "district": "Ranchi",
                "state": "Jharkhand"
            },
            dynamic_manifest={"hq": True, "government_entity": True},
            created_at=dates_pool[date_idx]
        )
        session.add(buyer_node)
        date_idx += 1
        
        # Flush to get buyer_node.id
        await session.flush()

        # Generate 500 compliant sellers
        compliant_sellers = []
        for i in range(1, 501):
            seller = Node(
                tenant_id=tenant_id,
                name=f"Compliant Seller {i:03d}",
                type="seller",
                industry_attributes={
                    "gstin": generate_jharkhand_gstin(),
                    "bank_verified": True,
                    "vehicle_year": int(np.random.randint(2020, 2027))
                },
                dynamic_manifest={"verification_status": "COMPLIANT"},
                created_at=dates_pool[date_idx]
            )
            session.add(seller)
            compliant_sellers.append(seller)
            date_idx += 1

        # Generate 30 disqualified sellers (15 vehicle non-compliant, 15 bank unverified)
        disqualified_sellers_vehicle = []
        disqualified_sellers_bank = []
        
        for i in range(1, 16):
            seller_veh = Node(
                tenant_id=tenant_id,
                name=f"Non-Compliant Vehicle Seller {i:02d}",
                type="seller",
                industry_attributes={
                    "gstin": generate_jharkhand_gstin(),
                    "bank_verified": True,
                    "vehicle_year": int(np.random.randint(2015, 2020)) # < 2020
                },
                dynamic_manifest={"verification_status": "DISQUALIFIED_VEHICLE"},
                created_at=dates_pool[date_idx]
            )
            session.add(seller_veh)
            disqualified_sellers_vehicle.append(seller_veh)
            date_idx += 1

            seller_bnk = Node(
                tenant_id=tenant_id,
                name=f"Unverified Bank Seller {i:02d}",
                type="seller",
                industry_attributes={
                    "gstin": generate_jharkhand_gstin(),
                    "bank_verified": False, # bank_unverified
                    "vehicle_year": int(np.random.randint(2020, 2027))
                },
                dynamic_manifest={"verification_status": "DISQUALIFIED_BANK"},
                created_at=dates_pool[date_idx]
            )
            session.add(seller_bnk)
            disqualified_sellers_bank.append(seller_bnk)
            date_idx += 1

        # Flush to populate IDs for flows
        await session.flush()

        # Seed 50 anomalous Maverick Spend records
        # Purchase agreements lacking verified nodal approvals
        for i in range(1, 51):
            source = np.random.choice(compliant_sellers)
            flow = Flow(
                tenant_id=tenant_id,
                name=f"Maverick Purchase Agreement {i:02d}",
                source_node_id=source.id,
                target_node_id=buyer_node.id,
                industry_attributes={
                    "amount": float(np.random.choice([15000, 32000, 75000, 120000])),
                    "nodal_approved": False # lacks verified approval
                },
                dynamic_manifest={
                    "maverick_spend": True,
                    "contract_type": "purchase_agreement"
                },
                created_at=dates_pool[date_idx]
            )
            session.add(flow)
            date_idx += 1

        # Seed 30 disqualified bids
        # 15 matching gate.vehicle_year_non_compliant
        for i in range(15):
            source = disqualified_sellers_vehicle[i]
            flow = Flow(
                tenant_id=tenant_id,
                name=f"Disqualified Vehicle Bid {i+1:02d}",
                source_node_id=source.id,
                target_node_id=buyer_node.id,
                industry_attributes={
                    "bid_amount": float(np.random.choice([85000, 92000, 105000])),
                    "vehicle_year": source.industry_attributes["vehicle_year"]
                },
                dynamic_manifest={
                    "disqualification_reason": "gate.vehicle_year_non_compliant",
                    "contract_type": "bid"
                },
                created_at=dates_pool[date_idx]
            )
            session.add(flow)
            date_idx += 1

        # 15 matching gate.bank_unverified
        for i in range(15):
            source = disqualified_sellers_bank[i]
            flow = Flow(
                tenant_id=tenant_id,
                name=f"Disqualified Bank Bid {i+1:02d}",
                source_node_id=source.id,
                target_node_id=buyer_node.id,
                industry_attributes={
                    "bid_amount": float(np.random.choice([88000, 95000, 110000])),
                    "bank_verified": source.industry_attributes["bank_verified"]
                },
                dynamic_manifest={
                    "disqualification_reason": "gate.bank_unverified",
                    "contract_type": "bid"
                },
                created_at=dates_pool[date_idx]
            )
            session.add(flow)
            date_idx += 1

        # Seed 500 compliant bids flows for the compliant sellers
        for i in range(500):
            source = compliant_sellers[i]
            flow = Flow(
                tenant_id=tenant_id,
                name=f"Compliant Bid {i+1:03d}",
                source_node_id=source.id,
                target_node_id=buyer_node.id,
                industry_attributes={
                    "bid_amount": float(np.random.randint(50000, 250000)),
                    "vehicle_year": source.industry_attributes["vehicle_year"],
                    "bank_verified": source.industry_attributes["bank_verified"]
                },
                dynamic_manifest={
                    "contract_type": "bid",
                    "compliant": True
                },
                created_at=dates_pool[date_idx]
            )
            session.add(flow)
            date_idx += 1

        print("Successfully structured all items in database transaction.")
        
    print("Database session completed and successfully committed to database.")


if __name__ == "__main__":
    asyncio.run(main())
