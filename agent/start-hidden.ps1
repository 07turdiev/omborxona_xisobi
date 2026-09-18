# Agentni oynasiz ishga tushiradi va chiqishni jurnalga yozadi.
#
# Bu faylni qo'lda yugurtirish shart emas — uni `install-service.ps1`
# yaratgan rejalashtirilgan vazifa chaqiradi. Qo'lda sinash uchun esa
# oddiygina `npm start` qulayroq: unda xabarlar ekranda ko'rinadi.

Set-Location -Path $PSScriptRoot

node index.js *>> agent.log
