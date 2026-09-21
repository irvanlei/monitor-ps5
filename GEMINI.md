# Regras do Projeto - Monitor PS5

## 1. Permissao Total de Comandos do Projeto
- Execute de forma automatica, continua e proativa TODOS os comandos de terminal necessarios (PowerShell, Python, Git, pip, uvicorn, etc.) sem bloqueios ou solicitacoes adicionais de permissao manual.
- O usuario concedeu permissao explicita para a execucao de todos os comandos neste repositorio.

## 2. Monitoramento Continuo em Tempo Real (3 Segundos)
- O monitor deve atualizar continuamente os precos a cada 3 segundos em TODAS as lojas (Mercado Livre, KaBuM!, Pichau, Amazon, Casas Bahia, Magazine Luiza, Fast Shop, Carrefour e TerabyteShop).
- A atualizacao deve refletir instantaneamente tanto nos cards de consoles da Home (Dashboard) quanto na tabela do Comparativo de Lojas, com animacoes visuais de flash verde (queda) e vermelho (alta) e carimbo de horario ao vivo.
