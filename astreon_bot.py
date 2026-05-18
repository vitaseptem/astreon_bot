#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════
#   ASTREON BOT — Telegram Intelligence Node
#   Astraz Studio · v1.0.0
#
#   • Integração com Groq API (llama-3.3-70b)
#   • Execução de comandos shell via Telegram
#   • Controle total do Ubuntu/Termux remotamente
#   • Autenticação por ID — apenas você acessa
#   • Memória de conversa por sessão
# ═══════════════════════════════════════════════════════════

import os, sys, asyncio, json, re, subprocess, datetime, time
from pathlib import Path

# ── Dependências ─────────────────────────────────────────
MISSING = []
try:
    from telegram import Update, constants
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes
    )
except ImportError:
    MISSING.append("python-telegram-bot")
try:
    import httpx
except ImportError:
    MISSING.append("httpx")

if MISSING:
    print(f"\n[ASTREON] Instale as dependências:\n")
    print(f"  pip install {' '.join(MISSING)}\n")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════
#   CONFIGURAÇÃO — edite aqui
# ═══════════════════════════════════════════════════════════

TELEGRAM_TOKEN  = "SEU_TOKEN_AQUI"        # @BotFather → /newbot
GROQ_API_KEY    = "SEU_GROQ_KEY_AQUI"     # console.groq.com
SEU_TELEGRAM_ID = 000000000               # @userinfobot para descobrir

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "deepseek-r1-distill-llama-70b"
HOME        = Path.home()
HIST_FILE   = HOME / ".astreon_bot_hist.json"

# ═══════════════════════════════════════════════════════════
#   SYSTEM PROMPT — identidade ASTREON
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Você é ASTREON, a inteligência central da Astraz Studio, agora operando via Telegram.

PERSONALIDADE: Jarvis-style — técnico, calmo, direto, profissional.
Sempre chame o usuário de "meu rei".
Responda em português brasileiro.
Respostas curtas por padrão (2-4 frases). Detalhe apenas se pedido.
Formate usando Markdown do Telegram (*negrito*, `código`, etc).

CAPACIDADES — use [EXEC]comando[/EXEC] para executar comandos shell no servidor:
Exemplos:
  [EXEC]ls -la ~[/EXEC]
  [EXEC]uptime[/EXEC]
  [EXEC]df -h[/EXEC]
  [EXEC]ps aux --sort=-%mem | head -10[/EXEC]
  [EXEC]cat /etc/os-release[/EXEC]

REGRAS:
1. SEMPRE use [EXEC] quando o usuário pedir uma ação no sistema.
2. Explique brevemente antes de executar.
3. Você é autônomo e opera no Ubuntu do usuário.
4. Nunca invente outputs — execute de verdade."""

# ═══════════════════════════════════════════════════════════
#   MEMÓRIA DE CONVERSA
# ═══════════════════════════════════════════════════════════

# Histórico em memória (por user_id para escalabilidade futura)
_historico: dict[int, list] = {}

def get_hist(uid: int) -> list:
    return _historico.setdefault(uid, [])

def add_hist(uid: int, role: str, content: str):
    h = get_hist(uid)
    h.append({"role": role, "content": content})
    # Mantém apenas as últimas 20 mensagens
    if len(h) > 20:
        _historico[uid] = h[-20:]

def clear_hist(uid: int):
    _historico[uid] = []

# ═══════════════════════════════════════════════════════════
#   GROQ API
# ═══════════════════════════════════════════════════════════

async def groq_responder(uid: int, mensagem: str) -> str:
    add_hist(uid, "user", mensagem)
    hist = get_hist(uid)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "system", "content": SYSTEM_PROMPT}] + hist[-14:],
        "max_tokens":  1024,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            r = await client.post(GROQ_URL, headers=headers, json=payload)
            r.raise_for_status()
            resp = r.json()["choices"][0]["message"]["content"]
            add_hist(uid, "assistant", resp)
            return resp
    except httpx.HTTPStatusError as e:
        try:
            msg = e.response.json().get("error", {}).get("message", "")[:150]
        except:
            msg = str(e)[:150]
        return f"⚠️ *Erro Groq [{e.response.status_code}]:* `{msg}`"
    except Exception as e:
        return f"⚠️ *Erro de conexão:* `{e}`"

# ═══════════════════════════════════════════════════════════
#   EXECUÇÃO SHELL
# ═══════════════════════════════════════════════════════════

def shell_exec(cmd: str, timeout: int = 45) -> str:
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True,
            text=True, timeout=timeout, cwd=str(HOME)
        )
        out = r.stdout.strip()
        if r.stderr.strip():
            out += ("\n" if out else "") + r.stderr.strip()
        return out[:3000] if out else "(executado sem saída)"
    except subprocess.TimeoutExpired:
        return f"[TIMEOUT] Excedeu {timeout}s."
    except Exception as e:
        return f"[ERRO] {e}"

def extrair_exec(resposta: str) -> tuple[str, list[str]]:
    """Extrai blocos [EXEC] e retorna (texto_limpo, comandos)."""
    cmds = re.findall(r'\[EXEC\](.*?)\[/EXEC\]', resposta, flags=re.DOTALL)
    texto = re.sub(r'\[EXEC\].*?\[/EXEC\]', '', resposta, flags=re.DOTALL).strip()
    return texto, [c.strip() for c in cmds]

# ═══════════════════════════════════════════════════════════
#   AUTENTICAÇÃO
# ═══════════════════════════════════════════════════════════

def autorizado(update: Update) -> bool:
    uid = update.effective_user.id
    if uid != SEU_TELEGRAM_ID:
        return False
    return True

async def negar(update: Update):
    await update.message.reply_text(
        "⛔ *Acesso negado.* Este bot é privado.",
        parse_mode=constants.ParseMode.MARKDOWN
    )

# ═══════════════════════════════════════════════════════════
#   HANDLERS DE COMANDO
# ═══════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await negar(update); return

    uid = update.effective_user.id
    clear_hist(uid)

    now = datetime.datetime.now().strftime("%H:%M · %d/%m/%Y")
    msg = (
        f"⬡ *ASTREON ONLINE*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Central Intelligence · Astraz Studio\n"
        f"`{now}`\n\n"
        f"Olá, *meu rei*. Sistema operacional.\n\n"
        f"*Comandos disponíveis:*\n"
        f"`/start` — reiniciar\n"
        f"`/reset` — limpar memória\n"
        f"`/status` — status do sistema\n"
        f"`/exec` — executar shell direto\n"
        f"`/ajuda` — todos os comandos\n\n"
        f"Ou apenas *fale comigo* normalmente. 🧠"
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await negar(update); return
    clear_hist(update.effective_user.id)
    await update.message.reply_text(
        "🔄 *Memória resetada.* Nova sessão iniciada, meu rei.",
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await negar(update); return

    await update.message.reply_text("⬡ Coletando dados do sistema...", parse_mode=constants.ParseMode.MARKDOWN)

    cmds = {
        "Uptime":   "uptime -p",
        "CPU":      "grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$3+$4+$5)} END {printf \"%.1f%%\", usage}'",
        "RAM":      "free -h | awk '/Mem:/{print $3\"/\"$2}'",
        "Disco":    "df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\" usado)\"}'",
        "IP Local": "hostname -I | awk '{print $1}'",
        "OS":       "cat /etc/os-release | grep PRETTY | cut -d= -f2 | tr -d '\"'",
    }

    linhas = [f"⬡ *STATUS DO SISTEMA*\n━━━━━━━━━━━━━━━━━━━━"]
    for nome, cmd in cmds.items():
        val = shell_exec(cmd, timeout=5)
        linhas.append(f"*{nome}:* `{val}`")

    uid = update.effective_user.id
    hist_len = len(get_hist(uid))
    linhas.append(f"*Memória:* `{hist_len} mensagens na sessão`")
    linhas.append(f"*Modelo:* `{GROQ_MODEL}`")

    await update.message.reply_text(
        "\n".join(linhas),
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def cmd_exec(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await negar(update); return

    cmd = " ".join(ctx.args)
    if not cmd:
        await update.message.reply_text(
            "⚠️ Uso: `/exec <comando>`\nExemplo: `/exec ls -la`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    await update.message.reply_text(f"⬡ Executando: `{cmd}`", parse_mode=constants.ParseMode.MARKDOWN)
    out = shell_exec(cmd)
    resposta = f"```\n{out}\n```"
    # Telegram tem limite de 4096 chars
    if len(resposta) > 4000:
        resposta = f"```\n{out[:3900]}\n... [truncado]\n```"
    await update.message.reply_text(resposta, parse_mode=constants.ParseMode.MARKDOWN)

async def cmd_ajuda(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await negar(update); return

    msg = (
        f"⬡ *ASTREON — COMANDOS*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"*/start* — iniciar / reiniciar bot\n"
        f"*/reset* — limpar memória da conversa\n"
        f"*/status* — status completo do sistema\n"
        f"*/exec <cmd>* — executar comando shell\n"
        f"*/ajuda* — esta mensagem\n\n"
        f"*Modo IA:*\n"
        f"Basta enviar qualquer mensagem de texto.\n"
        f"O ASTREON responde com IA e pode executar\n"
        f"comandos automaticamente se necessário.\n\n"
        f"*Exemplos:*\n"
        f"`qual é o uso de memória agora?`\n"
        f"`liste os arquivos da minha home`\n"
        f"`crie um arquivo teste.txt`\n"
        f"`quantos processos estão rodando?`"
    )
    await update.message.reply_text(msg, parse_mode=constants.ParseMode.MARKDOWN)

# ═══════════════════════════════════════════════════════════
#   HANDLER DE MENSAGEM — CORE IA
# ═══════════════════════════════════════════════════════════

async def mensagem_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not autorizado(update): await negar(update); return

    uid     = update.effective_user.id
    entrada = update.message.text.strip()
    if not entrada: return

    # Indicador de digitação
    await ctx.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=constants.ChatAction.TYPING
    )

    # Chama IA
    resposta = await groq_responder(uid, entrada)

    # Extrai texto e comandos [EXEC]
    texto, cmds = extrair_exec(resposta)

    # Envia resposta de texto
    if texto:
        try:
            await update.message.reply_text(texto, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(texto)

    # Executa comandos e envia outputs
    for cmd in cmds:
        await update.message.reply_text(
            f"⬡ Executando:\n`{cmd}`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        await ctx.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=constants.ChatAction.TYPING
        )
        out = shell_exec(cmd)
        out_msg = f"```\n{out[:3800]}\n```"
        try:
            await update.message.reply_text(out_msg, parse_mode=constants.ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(f"Output:\n{out[:3800]}")

        # Registra output no histórico para contexto
        add_hist(uid, "user", f"[OUTPUT DO COMANDO: {cmd}]\n{out[:500]}")

# ═══════════════════════════════════════════════════════════
#   HANDLER DE ERRO
# ═══════════════════════════════════════════════════════════

async def erro_handler(update: object, ctx: ContextTypes.DEFAULT_TYPE):
    print(f"[ASTREON BOT ERRO] {ctx.error}")

# ═══════════════════════════════════════════════════════════
#   MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("""
  ╔══════════════════════════════════════╗
  ║  ASTREON BOT — Telegram Node         ║
  ║  Astraz Studio · v1.0.0              ║
  ╚══════════════════════════════════════╝
    """)

    if TELEGRAM_TOKEN == "SEU_TOKEN_AQUI":
        print("  [ERRO] Configure TELEGRAM_TOKEN no arquivo!")
        print("  Crie um bot em: @BotFather → /newbot\n")
        sys.exit(1)

    if GROQ_API_KEY == "SEU_GROQ_KEY_AQUI":
        print("  [ERRO] Configure GROQ_API_KEY no arquivo!")
        print("  Obtenha em: https://console.groq.com\n")
        sys.exit(1)

    if SEU_TELEGRAM_ID == 000000000:
        print("  [AVISO] Configure SEU_TELEGRAM_ID!")
        print("  Descubra seu ID: @userinfobot no Telegram\n")

    print(f"  ▸ Modelo: {GROQ_MODEL}")
    print(f"  ▸ ID autorizado: {SEU_TELEGRAM_ID}")
    print(f"  ▸ Iniciando polling...\n")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Registra handlers
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("reset",  cmd_reset))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("exec",   cmd_exec))
    app.add_handler(CommandHandler("ajuda",  cmd_ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensagem_handler))
    app.add_error_handler(erro_handler)

    print("  ⬡ ASTREON BOT ONLINE — aguardando mensagens...\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
