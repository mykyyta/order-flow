# Міграція прод (OrderFlow → Pult)

Міграція завершена. Прод працює на **pult-app**, **pult-migrate**, секрети **pult-***, Terraform state **pult/prod**.

Старий сервіс `orderflow-app` і job `orderflow-migrate` можна видалити в GCP вручну, якщо ще не видалені.
