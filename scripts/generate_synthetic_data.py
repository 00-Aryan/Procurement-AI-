import asyncio
import os
import sys
import uuid
import random
import string
from datetime import datetime, timezone
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
    # ponytail: replaced np.random.choice with native random.choices/choice (DEBT-004)
    pan_letters = "".join(random.choices(string.ascii_uppercase, k=5))
    pan_numbers = "".join(random.choices(string.digits, k=4))
    entity_indicator = random.choice(string.ascii_uppercase)
    entity_number = random.choice(string.digits[1:])
    check_digit = random.choice(string.ascii_uppercase + string.digits)
    return f"20{pan_letters}{pan_numbers}{entity_indicator}{entity_number}Z{check_digit}"


def generate_dates(num_records: int) -> list[datetime]:
    """Generates dates uniformly within Q1 and Q2 2026 range boundaries."""
    # ponytail: replaced pandas DataFrame / datetime instantiations and numpy random with native datetime and random (DEBT-004)
    start_ts = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    end_ts = int(datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    return [datetime.fromtimestamp(random.randint(start_ts, end_ts), tz=timezone.utc) for _ in range(num_records)]


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
                    "vehicle_year": random.randint(2020, 2026)
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
                    "vehicle_year": random.randint(2015, 2019) # < 2020
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
                    "vehicle_year": random.randint(2020, 2026)
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
            source = random.choice(compliant_sellers)
            flow = Flow(
                tenant_id=tenant_id,
                name=f"Maverick Purchase Agreement {i:02d}",
                source_node_id=source.id,
                target_node_id=buyer_node.id,
                industry_attributes={
                    "amount": float(random.choice([15000, 32000, 75000, 120000])),
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
                    "bid_amount": float(random.choice([85000, 92000, 105000])),
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
                    "bid_amount": float(random.choice([88000, 95000, 110000])),
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
                    "bid_amount": float(random.randint(50000, 249999)),
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
