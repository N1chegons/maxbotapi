import http.client
import json
import os

from src.config import settings
import requests
import json

conn = http.client.HTTPSConnection("enter.tochka.com")

payload = json.dumps({
  "Data": {
    "accountId": "40802810709500018912/044525104",
    "customerCode": "301970249",
    "SecondSide": {
      "accountId": "40702810801000028776/044525555",
      "legalAddress": "400002, РОССИЯ, ВОЛОГОДСКАЯ ОБЛ, ВОЛГОГРАД г, МИРОЗОВСКАЯ ул, ДОМ 69, офис КВ. 1",
      "kpp": "346001001",
      "bankName": "ПАО БАНК ПСБ",
      "bankCorrAccount": "30101810400000000555",
      "taxCode": "3460071285",
      "type": "company",
      "secondSideName": "ООО ВЭС"
    },
    "Content": {
      "Invoice": {
        "Positions": [
          {
            "positionName": "Название товара",
            "unitCode": "шт.",
            "ndsKind": "nds_0",
            "price": "1234.56",
            "quantity": "1234.567",
            "totalAmount": "1234.56",
            "totalNds": "1234.56"
          }
        ],
        "date": "2026-04-25",
        "totalAmount": "0",
        "totalNds": "0",
        "number": "1",
        "basedOn": "Основание платежа",
        "comment": "Комментарий к платежу",
        "paymentExpiryDate": "2026-04-30"
      }
    }
  }
})

headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Authorization': f'Bearer {settings.JWT_TOKEN_TOCHKA_API}'
}

conn.request("POST", "/uapi/invoice/v1.0/bills", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))