# Política de Segurança (Security Policy)

## 🛡️ Versões Suportadas

Correções de segurança e melhorias defensivas são aplicadas ativamente na versão principal:

| Versão | Suportada |
| :--- | :--- |
| `1.0.x` (latest main) | :white_check_mark: |
| `< 1.0.0` | :x: |

---

## 🚨 Como Reportar uma Vulnerabilidade

Se você descobrir uma vulnerabilidade de segurança neste projeto:

1. **NÃO crie uma Issue pública** detalhando a falha ou potenciais formas de exploração.
2. Utilize o recurso oficial do GitHub: **[Private Vulnerability Reporting](https://github.com/SEU_USUARIO/TelegramDownloader/security/advisories/new)**.
3. Caso o repositório não possua o formulário privado habilitado, entre em contato diretamente com o mantenedor do repositório através de canal privado.
4. Por favor, inclua:
   - Descrição detalhada da vulnerabilidade;
   - Passos reprodutíveis ou prova de conceito mínima (sem credenciais reais);
   - Impacto potencial estimado.

Agradecemos e valorizamos a divulgação responsável.

---

## ⚠️ Cuidados com Credenciais e Dados Sensíveis

Ao utilizar ou contribuir para este projeto:

- **Arquivos `.session`**: Contêm chaves criptográficas ativas de autenticação no Telegram. Trate-os como senhas de altíssima criticidade. Nunca anexe arquivos de sessão a issues, e-mails ou mensagens de chat.
- **`api_id` e `api_hash`**: São identificadores da sua aplicação no Telegram. Mantenha-os protegidos em variáveis de ambiente ou em seu `config.json` local (que está no `.gitignore`).
- **Logs e Banco SQLite**: O banco `downloads.db` e os arquivos em `logs/` podem conter metadados e histórico de canais aos quais você tem acesso. Nunca os versione publicamente.

---

## 📋 Checklist de Segurança para o Mantenedor no GitHub

Ao publicar este repositório no GitHub, habilite as seguintes opções nas configurações do repositório (**Settings -> Code security and analysis**):

- [x] **Dependabot alerts**: Ativado.
- [x] **Dependabot security updates**: Ativado.
- [x] **Secret scanning**: Ativado.
- [x] **Push protection**: Ativado.
- [x] **Private vulnerability reporting**: Ativado.
- [x] **CodeQL analysis**: Ativado via GitHub Actions (`.github/workflows/codeql.yml`).
