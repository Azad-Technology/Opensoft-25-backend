import asyncio
from random import randint
from utils.config import get_async_database
from faker import Faker

async def create_employees_collection():
    # Initialize database connection
    async_db = get_async_database()
    fake = Faker()

    # Clear existing collection if needed
    await async_db.employees.delete_many({})

    employees_data = []
    
    for i in range(1, 501):
        emp_id = f"EMP{str(i).zfill(4)}"
        
        employee_record = {
            "employee_id": emp_id,
            "leave_balance": {
                "sick_leave": randint(1, 10),
                "casual_leave": randint(1, 10),
                "annual_leave": randint(1, 10),
                "unpaid_leave": randint(1, 10)
            },
            "team_id": randint(1, 7),
            "name": fake.name(),
            "email": f"{emp_id.lower()}@deloitte.com",
            "position": fake.job(),
            "date_of_joining": fake.date_between(start_date='-5y', end_date='today').isoformat()
        }
        
        employees_data.append(employee_record)

    try:
        # Insert all employee records
        result = await async_db.employees.insert_many(employees_data)
        print(f"Successfully created {len(result.inserted_ids)} employee records")
        
        # Verify count
        count = await async_db.employees.count_documents({})
        print(f"Total employees in collection: {count}")
        
    except Exception as e:
        print(f"Error creating employees collection: {e}")

if __name__ == "__main__":
    asyncio.run(create_employees_collection())