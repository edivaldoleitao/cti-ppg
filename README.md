# Documentação das Relações Semânticas - Vocabulário CTI

Este documento detalha as conexões lógicas (relationships) estabelecidas no vocabulário OML (`cti.oml`). [cite_start]Essas relações foram criadas para permitir a rastreabilidade do conhecimento e conectar as diferentes entidades do ecossistema de pós-graduação[cite: 60].

## Resumo das Relações

A tabela abaixo descreve cada relação, sua origem (`from`), seu destino (`to`) e a sua função semântica dentro do escopo do projeto:

| Relação | Origem (`from`) | Destino (`to`) | Descrição |
| :--- | :--- | :--- | :--- |
| **`sediado`** | `PPG` | `ICT` | Indica a Instituição de Ciência e Tecnologia (ICT) onde o Programa de Pós-Graduação (PPG) está localizado e operando. |
| **`avaliado`** | `PPG` | `Conceito_PPG` | [cite_start]Vincula o PPG ao seu respectivo Conceito_PPG, ou seja, à nota de avaliação quadrienal atribuída pela CAPES[cite: 61]. |
| **`vinculado`** | `Discente` | `PPG` | [cite_start]Associa o estudante (Discente) ao seu respectivo programa de pós-graduação de origem[cite: 63]. |
| **`membro`** | `Docente` | `PPG` | [cite_start]Associa o professor/pesquisador (Docente) ao programa de pós-graduação no qual atua[cite: 63]. |
| **`autoria`** | `Autor` | `Producao_Cientifica` | Conecta o pesquisador (Autor) aos artefatos de conhecimento (artigos, trabalhos) que ele produziu. |
| **`publicada`** | `Producao_Cientifica` | `Veiculo_Publicacao` | [cite_start]Conecta a Produção Científica ao seu respectivo Veículo de Publicação (revista, periódico ou anais de conferência), permitindo avaliar o prestígio por meio de métricas como o quartil da Scopus[cite: 58, 62]. |
| **`mensurado`** | `Autor` | `Citacao` | [cite_start]Relaciona o impacto bibliométrico (Citação, como Índice H ou i10) diretamente ao pesquisador responsável[cite: 62]. |
| **`orientador`** | `Discente` | `Docente` | Estabelece a relação de orientação acadêmica entre um estudante (Discente) e seu professor (Docente). |

---
[cite_start]**Nota Técnica:** Estas relações são fundamentais para responder à pergunta de pesquisa da Temática 4, pois criam o caminho semântico que liga a nota da CAPES (`avaliado`) ao volume de publicações e ao impacto gerado (`autoria`, `publicada` e `mensurado`)[cite: 11, 81].
