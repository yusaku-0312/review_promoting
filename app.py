import os
import secrets
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for, jsonify

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Generate a secret key if one doesn't exist
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Mock Dify API Key - In production, use environment variable
DIFY_API_KEY = os.environ.get('DIFY_API_KEY', 'key-placeholder')
# Dify API requires a specific Base URL usually, or full URL
DIFY_API_URL = os.environ.get('DIFY_API_URL', 'https://api.dify.ai/v1/chat-messages')

# Shop Data (Mock Database)
SHOPS = [
    {
        "id": "shop_001",
        "salon_name": "Review Salon Aoyama",
        "url": "https://g.page/r/example1/review"
    },
    {
        "id": "shop_002",
        "salon_name": "Review Salon Shibuya",
        "url": "https://g.page/r/example2/review"
    },
    {
        "id": "shop_003",
        "salon_name": "Review Salon Ginza",
        "url": "https://g.page/r/example3/review"
    }
]

def get_shop_by_id(shop_id):
    """Helper to find shop by ID"""
    return next((s for s in SHOPS if s["id"] == shop_id), None)

@app.route('/')
def index():
    """Step 1: Shop Selection"""
    return render_template('select_shop.html', shops=SHOPS)

@app.route('/set_shop', methods=['POST'])
def set_shop():
    """Save selected shop to session"""
    shop_id = request.form.get('shop_id')
    shop = get_shop_by_id(shop_id)
    if shop:
        session['shop'] = shop
        return redirect(url_for('input_info'))
    return redirect(url_for('index'))

@app.route('/input')
def input_info():
    """Step 2: Input Treatment Info"""
    shop = session.get('shop')
    if not shop:
        return redirect(url_for('index'))
    return render_template('input_info.html', shop=shop)

@app.route('/generate', methods=['POST'])
def generate_message():
    """Process input and call Dify API"""
    shop = session.get('shop')
    if not shop:
        return redirect(url_for('index'))

    # Collect Form Data
    services = request.form.getlist('services')
    style_request = request.form.get('style_request', '')
    special_tech = request.form.get('special_tech', '')
    hair_length = request.form.get('hair_length', '')
    hair_firmness = request.form.get('hair_firmness', '')
    stylist_name = request.form.get('stylist_name', '')
    # Proposal is currently manual input in requirement, but also mentions AI generation.
    # Requirement says: "文章構成３の提案文についてはAPI経由でDifyを利用し文章生成"
    
    treatment_info = {
        "services": ", ".join(services),
        "style": style_request,
        "tech": special_tech,
        "type": f"{hair_length}, {hair_firmness}",
        "stylist": stylist_name
    }

    # Construct the query for Dify
    dify_query = f"""
    以下の施術情報を元に、お客様へのおすすめヘアケア法やスタイリング剤等の提案文を50文字〜100文字程度で作成してください。
    
    【施術情報】
    ・利用したサービス: {treatment_info['services']}
    ・リクエストしたスタイル: {treatment_info['style']}
    ・特殊技術: {treatment_info['tech']}
    ・髪のタイプ: {treatment_info['type']}
    """

    # Call Dify API
    ai_proposal = ""
    try:
        headers = {
            'Authorization': f'Bearer {DIFY_API_KEY}',
            'Content-Type': 'application/json'
        }
        data = {
            "inputs": {},
            "query": dify_query,
            "response_mode": "blocking", # Using blocking for simplicity in MVP
            "user": "app-user",
            "files": []
        }
        
        if DIFY_API_KEY != 'key-placeholder':
            # Increased timeout to 60s as Dify generation can arguably take longer than 10s
            response = requests.post(DIFY_API_URL, headers=headers, json=data, timeout=90)
            if response.status_code == 200:
                result_json = response.json()
                ai_proposal = result_json.get('answer', '')
            else:
                print(f"Dify API Error: {response.status_code} - {response.text}")
                ai_proposal = "（AI提案文の生成に失敗しました。手動で入力してください。）"
        else:
             # Mock Response if no key
             ai_proposal = "（デモ）お客様の髪質は柔らかめですので、今のトリートメントを継続することで美しい色味を長く楽しめます。次回は少し早めのメンテナンスがおすすめです！"

    except Exception as e:
        print(f"Error calling Dify API: {e}")
        ai_proposal = "（エラーが発生しました。申し訳ありません。）"

    # Save to session for display
    session['generated_content'] = {
        "treatment_info": treatment_info,
        "ai_proposal": ai_proposal
    }
    
    return redirect(url_for('result_page'))

@app.route('/result')
def result_page():
    """Step 3: Display and Edit Message"""
    shop = session.get('shop')
    content = session.get('generated_content')
    
    if not shop or not content:
        return redirect(url_for('index'))
        
    # Construct initial full text
    text_1 = "本日はご来店ありがとうございました！今日の施術カルテをまとめましたので次回の参考にどうぞ！"
    text_2 = f"・利用したサービス：{content['treatment_info']['services']}\n" \
             f"・リクエストしたスタイル：{content['treatment_info']['style']}\n" \
             f"・特殊技術：{content['treatment_info']['tech']}\n" \
             f"・髪のタイプ：{content['treatment_info']['type']}\n" \
             f"・担当スタイリスト：{content['treatment_info']['stylist']}"
    text_url = f"こちらのURLから口コミも書いていただけると嬉しいです！（{shop['url']}）"
    text_3 = content['ai_proposal']
    
    full_text = f"{text_1}\n\n{text_2}\n\n{text_url}\n\n{text_3}"
    
    return render_template('result.html', shop=shop, shops=SHOPS, full_text=full_text)

@app.route('/update_shop_url', methods=['POST'])
def update_shop_url():
    """Web API to get URL for a specific shop (for frontend JS updates)"""
    data = request.get_json()
    shop_id = data.get('shop_id')
    shop = get_shop_by_id(shop_id)
    if shop:
        # Also update session to keep state consistent if they reload
        session['shop'] = shop
        return jsonify({"success": True, "url": shop['url'], "salon_name": shop['salon_name']})
    return jsonify({"success": False}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
