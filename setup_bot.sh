#!/bin/bash
# ═══════════════════════════════════════════════════════════
#   ASTREON BOT — Setup Script
#   Astraz Studio · Ubuntu/Termux
# ═══════════════════════════════════════════════════════════

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
WHT='\033[1;37m'
NC='\033[0m'

echo ""
echo -e "  ${RED}╔══════════════════════════════════════╗${NC}"
echo -e "  ${RED}║${NC}  ${WHT}ASTREON BOT — Setup${NC}               ${RED}║${NC}"
echo -e "  ${RED}║${NC}  ${NC}Astraz Studio · Ubuntu/Termux${NC}      ${RED}║${NC}"
echo -e "  ${RED}╚══════════════════════════════════════╝${NC}"
echo ""

echo -e "  ${RED}▸${NC} Atualizando pip..."
pip install --upgrade pip -q

echo -e "  ${RED}▸${NC} Instalando dependências..."
pip install python-telegram-bot httpx -q

echo ""
echo -e "  ${GRN}✓ Dependências instaladas!${NC}"
echo ""
echo -e "  ${YLW}PRÓXIMOS PASSOS:${NC}"
echo ""
echo -e "  ${RED}1.${NC} Abra o arquivo ${WHT}astreon_bot.py${NC}"
echo -e "     e configure as 3 variáveis no topo:"
echo ""
echo -e "     ${WHT}TELEGRAM_TOKEN${NC}  → @BotFather no Telegram → /newbot"
echo -e "     ${WHT}GROQ_API_KEY${NC}    → https://console.groq.com"
echo -e "     ${WHT}SEU_TELEGRAM_ID${NC} → envie uma msg para @userinfobot"
echo ""
echo -e "  ${RED}2.${NC} Rode o bot:"
echo -e "     ${WHT}python3 astreon_bot.py${NC}"
echo ""
echo -e "  ${RED}3.${NC} No Telegram, fale com seu bot e envie ${WHT}/start${NC}"
echo ""
echo -e "  ${RED}▸${NC} Para rodar em background (manter ativo):"
echo -e "     ${WHT}nohup python3 astreon_bot.py > astreon_bot.log 2>&1 &${NC}"
echo ""
echo -e "  ${GRN}⬡ ASTREON BOT pronto para configurar, meu rei.${NC}"
echo ""
