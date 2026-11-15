"""
Ops Copilot: synthetic data generator.

Populates the database defined in schema.sql with realistic fake data.
All data is invented. Nothing here comes from any real company.

Usage:
    python generate_data.py
"""

import random
from datetime import datetime, timedelta, date

import psycopg2

# ---------------------------------------------------------------
# config
# ---------------------------------------------------------------
DB = dict(
    host="localhost",
    port=5432,
    dbname="opscopilot",
    user="postgres",
    password="postgres",
)

SEED = 42  # fixed seed so the data is the same every run
N_CUSTOMERS = 200
N_MONTHS = 6  # how far back collections go
SUBSCRIPTION_EUR = 32.00

random.seed(SEED)

FIRST = [
    "Mary",
    "Tom",
    "Sean",
    "Aoife",
    "Liam",
    "Niamh",
    "Conor",
    "Sinead",
    "Patrick",
    "Ciara",
    "Declan",
    "Orla",
    "Eoin",
    "Roisin",
    "Cathal",
    "Fiona",
    "Brendan",
    "Sarah",
    "Kevin",
    "Emma",
]
LAST = [
    "Byrne",
    "Murphy",
    "Kelly",
    "O'Brien",
    "Ryan",
    "Walsh",
    "Doyle",
    "Dunne",
    "Kavanagh",
    "Nolan",
    "Brennan",
    "Lynch",
    "Moore",
    "Quinn",
    "Farrell",
    "Hughes",
    "Gallagher",
    "Duffy",
    "Casey",
    "Reilly",
]
BUSINESS = [
    "Bakery",
    "Hotel",
    "Cafe",
    "Garage",
    "Pharmacy",
    "Supermarket",
    "Restaurant",
    "Salon",
    "Warehouse",
    "Office Park",
]

ROUTES = [
    ("Route 1", "Clondalkin", "07-D-11234"),
    ("Route 2", "Tallaght", "09-D-44219"),
    ("Route 3", "Lucan", "12-D-70118"),
    ("Route 4", "Rathfarnham", "14-D-20993"),
    ("Route 5", "Blanchardstown", "16-D-55710"),
]

DRIVERS = [
    ("Tom Whelan", "EMP-001", False),  # left the company
    ("Sean Gallagher", "EMP-002", True),
    ("Martin Fahy", "EMP-003", True),
    ("Paul Traynor", "EMP-004", True),
    ("Dave Cullen", "EMP-005", True),
    ("Anna Kowalski", "EMP-006", True),
]

SUPPLIERS = [
    "XYZ Waste Disposal Ltd",
    "Leinster Haulage",
    "Midlands Recovery Ltd",
    "Coastal Materials",
]
MATERIALS = [
    "Mixed Recyclables",
    "Cardboard",
    "Residual Waste",
    "Organic Fines",
    "Plastics",
]


def eircode():
    routing = random.choice(["D22", "D24", "D12", "D14", "D15"])
    chars = "ACDEFHKNPRTVWXY0123456789"
    return f"{routing} {''.join(random.choices(chars, k=4))}"


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # ---------- routes ----------
    route_ids = []
    for name, area, reg in ROUTES:
        cur.execute(
            "INSERT INTO routes (name, area, vehicle_reg) VALUES (%s,%s,%s) "
            "RETURNING route_id",
            (name, area, reg),
        )
        route_ids.append(cur.fetchone()[0])

    # ---------- drivers ----------
    driver_ids = []
    for name, ref, active in DRIVERS:
        cur.execute(
            "INSERT INTO drivers (name, employee_ref, active) VALUES (%s,%s,%s) "
            "RETURNING driver_id",
            (name, ref, active),
        )
        driver_ids.append(cur.fetchone()[0])

    active_driver_ids = driver_ids[1:]  # everyone except Tom, who left
    tom_id = driver_ids[0]

    # ---------- customers ----------
    customer_ids = []
    today = date.today()
    for i in range(N_CUSTOMERS):
        commercial = random.random() < 0.20
        if commercial:
            name = f"{random.choice(LAST)}'s {random.choice(BUSINESS)}"
            acct = "commercial"
        else:
            name = f"{random.choice(FIRST)} {random.choice(LAST)}"
            acct = "household"
        status = "inactive" if random.random() < 0.05 else "active"
        created = datetime.combine(
            today - timedelta(days=random.randint(200, 1500)), datetime.min.time()
        )
        cur.execute(
            "INSERT INTO customers (name, account_type, eircode, route_id, "
            "status, created_at) VALUES (%s,%s,%s,%s,%s,%s) "
            "RETURNING customer_id",
            (name, acct, eircode(), random.choice(route_ids), status, created),
        )
        customer_ids.append((cur.fetchone()[0], acct, status))

    # ---------- collections ----------
    # Each active customer gets a lift roughly every two weeks per bin type.
    # December gets a volume bump so there is a seasonal pattern to find.
    start = today - timedelta(days=N_MONTHS * 30)
    n_collections = 0

    for cust_id, acct, cust_status in customer_ids:
        if cust_status == "inactive":
            continue
        day = start + timedelta(days=random.randint(0, 6))
        while day < today:
            bin_type = random.choices(
                ["general", "recycling", "organic"], weights=[4, 4, 2]
            )[0]

            # driver: Tom only appears in the first two months, then leaves
            months_in = (day - start).days / 30
            if months_in < 2 and random.random() < 0.25:
                driver = tom_id
            else:
                driver = random.choice(active_driver_ids)

            r = random.random()
            if r < 0.04:
                status, weight = "missed", None
            elif r < 0.11:
                status = "contaminated"
                weight = round(random.uniform(8, 30), 2)
            else:
                status = "collected"
                base = 25 if acct == "commercial" else 12
                weight = round(random.uniform(base * 0.5, base * 1.8), 2)

            # December bump
            if weight is not None and day.month == 12:
                weight = round(weight * random.uniform(1.15, 1.45), 2)

            ts = datetime.combine(day, datetime.min.time()) + timedelta(
                hours=random.randint(6, 16), minutes=random.choice([0, 15, 30, 45])
            )

            cur.execute(
                "INSERT INTO collections (customer_id, route_id, driver_id, "
                "collected_at, bin_type, weight_kg, status) "
                "VALUES (%s,(SELECT route_id FROM customers WHERE customer_id=%s),"
                "%s,%s,%s,%s,%s)",
                (cust_id, cust_id, driver, ts, bin_type, weight, status),
            )
            n_collections += 1

            step = 7 if day.month != 12 else 5  # more frequent in December
            day += timedelta(days=step + random.randint(-1, 1))

    # ---------- invoices ----------
    n_invoices = 0
    for cust_id, acct, cust_status in customer_ids:
        if cust_status == "inactive":
            continue
        amount = SUBSCRIPTION_EUR * (3.5 if acct == "commercial" else 1.0)
        for m in range(N_MONTHS):
            issued = today - timedelta(days=30 * (N_MONTHS - m))
            due = issued + timedelta(days=30)
            r = random.random()
            if r < 0.72:
                paid = issued + timedelta(days=random.randint(3, 29))
            elif r < 0.88:
                paid = issued + timedelta(days=random.randint(31, 75))
                if paid > today:
                    paid = None
            else:
                paid = None
            cur.execute(
                "INSERT INTO invoices (customer_id, issued_at, due_at, "
                "amount_eur, paid_at) VALUES (%s,%s,%s,%s,%s)",
                (cust_id, issued, due, round(amount, 2), paid),
            )
            n_invoices += 1

    # ---------- supplier dockets ----------
    for i in range(40):
        d = today - timedelta(days=random.randint(1, 180))
        tonnes = round(random.uniform(4, 26), 2)
        charge = round(tonnes * random.uniform(22, 40), 2)
        approved = random.random() < 0.65
        cur.execute(
            "INSERT INTO supplier_dockets (supplier, docket_date, material, "
            "tonnes, charge_eur, source_file, extracted_at, approved_by, "
            "approved_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                random.choice(SUPPLIERS),
                d,
                random.choice(MATERIALS),
                tonnes,
                charge,
                f"dockets/docket_{i+1:03d}.pdf",
                datetime.combine(d, datetime.min.time()) + timedelta(days=1),
                "Mary Byrne" if approved else None,
                (
                    datetime.combine(d, datetime.min.time()) + timedelta(days=2)
                    if approved
                    else None
                ),
            ),
        )

    conn.commit()

    for t in [
        "routes",
        "drivers",
        "customers",
        "collections",
        "invoices",
        "supplier_dockets",
    ]:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t:20s} {cur.fetchone()[0]:>6}")

    cur.close()
    conn.close()
    print("\nDone. All data is synthetic.")


if __name__ == "__main__":
    main()
