# Telegram_Downloader_CJrTools — v1.0.0

Primeira versão pública estável do **Telegram_Downloader_CJrTools**, um downloader modular, seguro e resiliente de arquivos e mídias do Telegram com suporte a downloads simultâneos, retomada automática (*auto-resume*), gravação atômica (`.part`), verificação de integridade via SHA-256 e catálogo completo em planilha CSV.

---

### 🌟 Destaques da Versão

- **Interface Gráfica Moderna (GUI em PyQt6)**: Totalmente reformulada no Design System *Dark, Flat, Minimal, Geometric & Technical*, com paleta industrial (`#2E2D2D`, `#FFAC2B`), tipografia Inter/JetBrains Mono e ícones Phosphor.
- **Aba "Sobre" e Identidade Visual**: Guia dedicada com informações de versão, autoria (CJRDOOM / Carlos Junior) e integração de logo de alta fidelidade.
- **Download Concorrente e Streaming**: Gerenciamento de múltiplos downloads paralelos com controle de fluxo em tempo real via semáforo assíncrono.
- **Download Atômico com `.part`**: Arquivos gravados temporariamente como `.part` e promovidos atomicamente apenas após validação de tamanho e integridade SHA-256.
- **Retomada Inteligente (*Resume*)**: Continuação automática de downloads interrompidos a partir do ponto exato onde pararam.
- **Varredura e Catálogo CSV**: Indexação prévia de todo o conteúdo do canal/grupo com estimativa de volume em disco e exportação protegida contra *CSV Formula Injection*.
- **Filtros Flexíveis**: Filtragem por inclusão (*whitelist*) e exclusão (*blacklist*) com normalização Unicode (insensível a acentos e maiúsculas/minúsculas).
- **Banco de Dados SQLite Local**: Controle transacional de estado de downloads, histórico e estatísticas em modo WAL.
- **Isolamento e Segurança**: Separação completa entre o código e dados do usuário (`%LOCALAPPDATA%`), sem exposição de credenciais ou arquivos `.session`.

---

### 📦 Instalação e Execução (Windows x64)

1. Baixe o executável `Telegram_Downloader_CJrTools.exe` abaixo.
2. (Opcional) Verifique a integridade do arquivo comparando seu hash SHA-256 com o valor listado no arquivo `SHA256SUMS.txt`.
3. Execute o aplicativo com dois cliques.

---

### 🔒 Requisitos
- Windows 10 ou 11 (64-bit).
- Credenciais de API do Telegram (`api_id` e `api_hash`) obtidas gratuitamente em [my.telegram.org](https://my.telegram.org).

---

### 🛡️ Checksums Oficiais (SHA-256)

```text
81f1cedcc8c24dbceae98c09aa720e3a1532eb0b6ca79fc6c04d4a86baa84ab6  Telegram_Downloader_CJrTools.exe
```

