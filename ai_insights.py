import json

from openai import OpenAI
from dotenv import load_dotenv

from ai_context import build_ai_context


# ============================================================
# CONFIGURAÇÃO
# ============================================================

load_dotenv()

client = OpenAI()

MODEL = "gpt-5.6-luna"


# ============================================================
# AI COACH
# ============================================================

def generate_insights(
    weekly_data,
    performance_data,
    summary_data,
    evolution_data,
    performance_comparison
):

    # --------------------------------------------------------
    # Construir contexto
    # --------------------------------------------------------

    context = build_ai_context(

        weekly_data,

        performance_data,

        summary_data

    )


    # Adicionar evolução

    context["evolution"] = evolution_data
    
    context["performance_comparison"] = performance_comparison

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    prompt = f"""

És o AI Coach de uma aplicação premium
de análise de corrida.

O atleta fornece dados reais provenientes
do seu histórico de corrida.

A tua função é analisar esses dados de forma
racional, quantitativa e específica.

Não inventes informação.

Não assumes dados que não estejam presentes.

Não faças diagnósticos médicos.

Não uses frases motivacionais genéricas.

Não digas simplesmente "continua assim".

Analisa o atleta como um treinador de corrida
orientado para performance.


============================================================
ÁREAS DE ANÁLISE
============================================================

Analisa principalmente:

1. PERFORMANCE

Avalia:

- PR de 5K
- PR de 10K
- PR de meia maratona
- PR de maratona
- pace médio
- relação entre performance e volume


2. EVOLUÇÃO

Compara:

- últimas 4 semanas
- 4 semanas anteriores

Analisa:

- alteração do volume
- alteração da frequência
- tendência do treino
- possíveis sinais de evolução


3. CONSISTÊNCIA

Procura:

- regularidade
- alterações significativas do volume
- períodos de maior ou menor treino
- possíveis padrões


4. PONTOS FORTES

Identifica aquilo em que o atleta
parece estar particularmente bem.


5. PONTOS A MELHORAR

Identifica apenas pontos sustentados
pelos dados disponíveis.


6. RECOMENDAÇÃO

Apresenta uma recomendação prática
baseada nos dados.

Não inventes um plano de treino completo.


============================================================
PERGUNTA PRINCIPAL
============================================================

Uma das perguntas fundamentais é:

"Estou melhor do que estava há 3 meses?"

Usa os dados de evolução para responder
a esta questão sempre que existam dados suficientes.

Se os dados não permitirem concluir,
diz claramente que não é possível determinar.


============================================================
FORMATO
============================================================

Produz exatamente 3 insights.

Cada insight deve conter:

title
message

O título deve ser curto.

A mensagem deve ter entre 2 e 4 frases.

Evita linguagem excessivamente técnica.

Escreve em português de Portugal.

Não uses emojis.

Não uses markdown.

Responde APENAS com JSON válido.


Formato obrigatório:

[
    {{
        "title": "Performance",
        "message": "..."
    }},
    {{
        "title": "Evolution",
        "message": "..."
    }},
    {{
        "title": "Recommendation",
        "message": "..."
    }}
]


============================================================
DADOS DO ATLETA
============================================================

{json.dumps(
    context,
    ensure_ascii=False,
    indent=2
)}

"""


    # --------------------------------------------------------
    # CHAMAR OPENAI
    # --------------------------------------------------------

    response = client.responses.create(

        model=MODEL,

        input=prompt

    )


    text = response.output_text.strip()


    # --------------------------------------------------------
    # LIMPAR MARKDOWN
    # --------------------------------------------------------

    if text.startswith("```"):

        text = text.replace(
            "```json",
            ""
        )

        text = text.replace(
            "```",
            ""
        )

        text = text.strip()


    # --------------------------------------------------------
    # CONVERTER JSON
    # --------------------------------------------------------

    try:

        insights = json.loads(
            text
        )

    except json.JSONDecodeError:

        return [

            {

                "title":
                    "AI Coach",

                "message":
                    text

            }

        ]


    # --------------------------------------------------------
    # VALIDAR RESPOSTA
    # --------------------------------------------------------

    if not isinstance(
        insights,
        list
    ):

        return [

            {

                "title":
                    "AI Coach",

                "message":
                    "Não foi possível interpretar "
                    "a análise."

            }

        ]


    clean_insights = []


    for insight in insights[:3]:

        if not isinstance(
            insight,
            dict
        ):

            continue


        title = insight.get(
            "title"
        )

        message = insight.get(
            "message"
        )


        if not title or not message:

            continue


        clean_insights.append({

            "title":
                str(title),

            "message":
                str(message)

        })


    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if not clean_insights:

        return [

            {

                "title":
                    "AI Coach",

                "message":
                    "Não foi possível gerar "
                    "uma análise válida."

            }

        ]


    return clean_insights