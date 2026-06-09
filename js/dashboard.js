Papa.parse(
    "data/producao_pe_scopus_somente_instituicoes_pe.csv",
{
    download: true,
    header: true,
    skipEmptyLines: true,

    complete: function(resultado){

        const dados = resultado.data;

        console.log("Registros carregados:", dados.length);

        gerarKPIs(dados);

        graficoPrograma(dados);
        graficoIES(dados);
        graficoAno(dados);
        graficoTopProgramas(dados);
        graficoConceito(dados);
        graficoIdioma(dados);
        graficoVeiculo(dados);
        graficoAutores(dados);
    }
});

function publicacoesUnicas(dados){

    const mapa = {};

    dados.forEach(row=>{

        let chave =
            row.PUB_KEY ||
            row.DS_DOI_FINAL ||
            row.SCOPUS_DOI ||
            row.ID_ADD_PRODUCAO_INTELECTUAL;

        if(!chave)
            return;

        if(!mapa[chave])
            mapa[chave] = row;
    });

    return Object.values(mapa);
}

function contar(coluna,dados){

    const mapa = {};

    dados.forEach(row=>{

        const valor = row[coluna];

        if(!valor)
            return;

        mapa[valor] =
            (mapa[valor] || 0) + 1;
    });

    return mapa;
}

function topN(mapa,n){

    return Object.entries(mapa)
        .sort((a,b)=>b[1]-a[1])
        .slice(0,n);
}

function abreviarIES(nome){

    if(!nome)
        return nome;

    return nome
        .replace(
            "UNIVERSIDADE FEDERAL DE PERNAMBUCO",
            "UFPE"
        )
        .replace(
            "UNIVERSIDADE FEDERAL RURAL DE PERNAMBUCO",
            "UFRPE"
        )
        .replace(
            "UNIVERSIDADE DE PERNAMBUCO",
            "UPE"
        )
        .replace(
            "UNIVERSIDADE CATOLICA DE PERNAMBUCO",
            "UNICAP"
        );
}

function gerarKPIs(dados){

    const pubs =
        publicacoesUnicas(dados);

    const programas =
        new Set(
            pubs.map(
                x => x.NM_PROGRAMA_IES
            )
        );

    const ies =
        new Set(
            pubs.map(
                x => x.NM_ENTIDADE_ENSINO
            )
        );

    const periodicos = new Set();

    pubs.forEach(row=>{

        let nome =
            row.SCOPUS_SOURCE ||
            row.NM_VEICULO_FINAL;

        if(!nome)
            return;

        nome = nome.trim();

        if(
            nome === "" ||
            nome === "-" ||
            nome.toLowerCase() === "null" ||
            nome.toLowerCase() === "undefined"
        ){
            return;
        }

        periodicos.add(nome);
    });

    document.getElementById(
        "kpi_programas"
    ).innerHTML =
        programas.size.toLocaleString();

    document.getElementById(
        "kpi_ies"
    ).innerHTML =
        ies.size.toLocaleString();

    document.getElementById(
        "kpi_publicacoes"
    ).innerHTML =
        pubs.length.toLocaleString();

    document.getElementById(
        "kpi_periodicos"
    ).innerHTML =
        periodicos.size.toLocaleString();
}

function graficoPrograma(dados){

    const top =
        topN(
            contar(
                "NM_PROGRAMA_IES",
                publicacoesUnicas(dados)
            ),
            15
        ).reverse();

    Plotly.newPlot(
        "grafico_programa",
        [{
            x: top.map(x=>x[1]),
            y: top.map(x=>x[0]),
            type:"bar",
            orientation:"h"
        }],
        {
            height:700,
            margin:{l:300}
        }
    );
}

function graficoIES(dados){

    const top =
        topN(
            contar(
                "NM_ENTIDADE_ENSINO",
                publicacoesUnicas(dados)
            ),
            10
        ).reverse();

    Plotly.newPlot(
        "grafico_ies",
        [{
            x: top.map(x=>x[1]),
            y: top.map(x=>abreviarIES(x[0])),
            text: top.map(x=>x[0]),
            type:"bar",
            orientation:"h",
            hovertemplate:
            "%{text}<br>Produções: %{x}<extra></extra>"
        }],
        {
            height:600,
            margin:{l:180}
        }
    );
}

function graficoAno(dados){

    const anos =
        contar(
            "AN_BASE",
            publicacoesUnicas(dados)
        );

    const x =
        Object.keys(anos).sort();

    Plotly.newPlot(
        "grafico_ano",
        [{
            x:x,
            y:x.map(a=>anos[a]),
            mode:"lines+markers"
        }],
        {
            height:500
        }
    );
}

function graficoTopProgramas(dados){

    const top =
        topN(
            contar(
                "NM_PROGRAMA_IES",
                publicacoesUnicas(dados)
            ),
            15
        ).reverse();

    Plotly.newPlot(
        "grafico_top_programas",
        [{
            x: top.map(x=>x[1]),
            y: top.map(x=>x[0]),
            type:"bar",
            orientation:"h"
        }],
        {
            height:700,
            margin:{l:300}
        }
    );
}

function graficoConceito(dados){

    const conceito =
        contar(
            "CD_CONCEITO_CURSO",
            publicacoesUnicas(dados)
        );

    Plotly.newPlot(
        "grafico_conceito",
        [{
            x:Object.keys(conceito),
            y:Object.values(conceito),
            type:"bar"
        }],
        {
            height:500
        }
    );
}

function graficoIdioma(dados){

    const top =
        topN(
            contar(
                "DS_IDIOMA",
                publicacoesUnicas(dados)
            ),
            10
        );

    Plotly.newPlot(
        "grafico_idioma",
        [{
            labels:top.map(x=>x[0]),
            values:top.map(x=>x[1]),
            type:"pie"
        }],
        {
            height:600
        }
    );
}

function graficoVeiculo(dados){

    const pubs = publicacoesUnicas(dados);

    const mapa = {};

    pubs.forEach(row=>{

        let veiculo =
            row.SCOPUS_SOURCE;

        if(
            !veiculo ||
            veiculo.trim() === ""
        ){
            veiculo =
                row.NM_VEICULO_FINAL;
        }

        if(!veiculo)
            return;

        veiculo = veiculo.trim();

        if(
            veiculo === "" ||
            veiculo === "-" ||
            veiculo.toLowerCase() === "null" ||
            veiculo.toLowerCase() === "undefined" ||
            veiculo.toLowerCase() === "não informado"
        ){
            return;
        }

        mapa[veiculo] =
            (mapa[veiculo] || 0) + 1;
    });

    const top = Object.entries(mapa)
        .sort((a,b)=>b[1]-a[1])
        .slice(0,7)
        .reverse();

    Plotly.newPlot(
        "grafico_veiculo",
        [{
            x: top.map(x=>x[1]),
            y: top.map(x=>x[0]),

            type:"bar",
            orientation:"h",

            text: top.map(x=>x[1]),
            textposition:"outside",

            hovertemplate:
                "<b>%{y}</b><br>" +
                "Publicações: %{x}" +
                "<extra></extra>"
        }],
        {
            height:600,

            margin:{
                l:450,
                r:80,
                t:20,
                b:40
            },

            xaxis:{
                title:"Quantidade de Publicações"
            },

            yaxis:{
                automargin:true
            }
        },
        {
            responsive:true
        }
    );
}

function graficoAutores(dados){

    const top =
        topN(
            contar(
                "NM_AUTOR",
                dados
            ),
            20
        ).reverse();

    Plotly.newPlot(
        "grafico_autores",
        [{
            x: top.map(x=>x[1]),
            y: top.map(x=>x[0]),
            type:"bar",
            orientation:"h"
        }],
        {
            height:900,
            margin:{
                l:350
            }
        }
    );
}