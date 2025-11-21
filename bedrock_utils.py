import boto3
from botocore.exceptions import ClientError
import json
import re

# -----------------------------
# AWS CLIENTS
# -----------------------------

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

bedrock_kb = boto3.client(
    service_name="bedrock-agent-runtime",
    region_name="us-east-1"
)


# -----------------------------
# CLASSIFIER
# -----------------------------

def valid_prompt(prompt, model_id):
    """
    Classify a prompt into categories A/B/C/D.
    """

    classification_prompt = f"""
Classify the user's message into exactly ONE label:
- A
- B
- C
- D

Definitions:
A → Greeting (hi, hello)
B → Heavy machinery general (e.g., forklift, bulldozer, excavator)
C → Heavy machinery technical (specs, engine, hydraulics, capacity)
D → Irrelevant / anything else

Examples:
User: "hi"
Label: A

User: "what is a forklift"
Label: B

User: "engine capacity of komatsu pc200"
Label: C

User: "what is phishing"
Label: D

Now classify:
User: "{prompt}"
Label:
"""

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps({
                "inputText": classification_prompt,
                "textGenerationConfig": {
                    "temperature": 0.0,
                    "topP": 1.0,
                    "maxTokenCount": 40
                }
            })
        )

        raw = json.loads(response["body"].read())["results"][0]["outputText"].strip().upper()

        # Normalize labels
        if raw.startswith("A"):
            return "A"
        if raw.startswith("B"):
            return "B"
        if raw.startswith("C"):
            return "C"
        return "D"

    except Exception as e:
        print(f"Error in valid_prompt: {e}")
        return "D"

# -----------------------------
# KB RETRIEVAL
# -----------------------------

def query_knowledge_base(query, kb_id):
    """
    Retrieve top KB chunks.
    """
    try:
        response = bedrock_kb.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 3
                }
            }
        )
        print("\n[DEBUG] Raw KB chunk structure:\n", json.dumps(response, indent=2))

        return response.get("retrievalResults", [])

    except ClientError as e:
        print(f"Error querying KB: {e}")
        return []


# -----------------------------
# GENERATION
# -----------------------------

def generate_response(prompt, kb_results, model_id, temperature, top_p):
    """
    Titan Text generation with KB summarization.
    Preserves user's titan_prompt EXACTLY, only preprocessing KB.
    """

    kb_text_raw = ""
    kb_sources = []

    # ----------------------------------------
    # 1) Extract KB raw text + sources
    # ----------------------------------------
    if kb_results:
        kb_parts = []
        for chunk in kb_results:
            content = chunk.get("content", {})
            text = content.get("text")
            if text:
                kb_parts.append(text)

            # Get filename
            loc = content.get("location", {})
            s3 = loc.get("s3Location", {})
            uri = s3.get("uri")
            key = s3.get("key")

            if uri:
                kb_sources.append(uri.split("/")[-1])
            elif key:
                kb_sources.append(key.split("/")[-1])
            else:
                kb_sources.append("[Unknown source]")

        kb_text_raw = "\n".join(kb_parts)

        # ----------------------------------------
        # 2) Summarize the KB text to avoid raw dump
        # ----------------------------------------
        summarization_prompt = f"""
Summarize the following technical document in **5 bullet points**.
Focus on purpose, capabilities, and engineering features.
Do NOT copy large sections of text.

[Document]
{kb_text_raw}
"""

        body = {
            "inputText": summarization_prompt,
            "textGenerationConfig": {
                "temperature": 0.0,
                "topP": 1.0,
                "maxTokenCount": 200
            }
        }

        summary_resp = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )

        summarized_kb = json.loads(summary_resp["body"].read())["results"][0]["outputText"]

    else:
        summarized_kb = None

    # If we have a summary, use that as KB text
    kb_text = summarized_kb if summarized_kb else None

    # ----------------------------------------
    # 3) TITAN PROMPT
    # ----------------------------------------
    source_list = ", ".join(kb_sources) if kb_sources else "None"

    titan_prompt = f"""
You are a friendly but professional assistant specialized in heavy machinery.

Use the knowledge base *only* if it is relevant.

Rules:
- If user greets you, greet normally.
- Answer in 2–5 sentences.
- If KB context is useful, integrate it naturally.
- You may reference documents by filename (e.g., "according to BD850.pdf")
- Do NOT reveal S3 paths or internal metadata.
- Do NOT hallucinate model names or specs not present in KB.
- Do NOT add follow-up questions like "Is there anything else I can help you with?" or similar closing sentences. End the response immediately after answering.

[Reference documents]
{source_list}

[Reference context]
{kb_text if kb_text else "None."}

[User question]
{prompt}

Answer clearly:
"""

    # ----------------------------------------
    # 4) Final Titan generation
    # ----------------------------------------
    try:
        final_body = {
            "inputText": titan_prompt,
            "textGenerationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "maxTokenCount": 300
            }
        }

        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(final_body)
        )

        return json.loads(response["body"].read())["results"][0]["outputText"].strip()

    except Exception as e:
        print(f"Error generating response: {e}")
        return ""
