# Document-Driven File Routing System

Sistema de automacao para extracao de IDs de documentos PDF e roteamento inteligente de arquivos entre diretorios.

## Funcionalidades

- Extracao de padroes numericos (8 digitos) de PDFs usando `pdfplumber`
- Busca automatica de arquivos relacionados em pasta fonte
- Copia com versionamento automatico (_v1, _v2) para subpastas organizadas
- Validacao de saldo para extratos bancarios
- Interface desktop com Tkinter (sem necessidade de email)

## Requisitos

```bash
pip install -r requirements.txt
```

## Uso

```bash
python app_routing.py
```

Para a versao com extracao financeira:
```bash
python app_tkinter.py
```

## Configuracao

Crie um arquivo `.env` baseado no `.env.example` para definir valores sensiveis como saldo esperado e diretorios padrao.

## Estrutura

- `app_routing.py` - Interface principal de roteamento de arquivos
- `app_tkinter.py` - Interface de extracao financeira
- `extractor.py` - Servico de extracao de tabelas PDF
- `processor.py` - Servico de validacao e processamento
- `pdf_service.py` - Servico de extracao de IDs
- `file_service.py` - Servico de gerenciamento de arquivos

## Licenca

MIT
