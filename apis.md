Notes: try to run the API to know how to parse the response.

## API token
export ARK_API_TOKEN="16997291-4771-4dc9-9a42-4acc930897fa"

## LLM API for getting keywords and insights
curl https://ark-cn-beijing.bytedance.net/api/v3/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ARK_API_TOKEN" \
  -d $'{
    "model": "ep-20250529215531-dfpgt",
    "messages": [
        {
            "content": [
                {
                    "image_url": {
                        "url": "https://ark-project.tos-cn-beijing.ivolces.com/images/view.jpeg"
                    },
                    "type": "image_url"
                },
                {
                    "text": "图片主要讲了什么?",
                    "type": "text"
                }
            ],
            "role": "user"
        }
    ]
}'

## embedding API to getting web record embedding, try to run the API to know how to parse the response.
curl https://ark-cn-beijing.bytedance.net/api/v3/embeddings/multimodal \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer $ARK_API_TOKEN" \
   -d '{
    "model": "ep-20250529220411-grkkv",
    "input": [
        {
            "type":"text",
            "text":"API Test, smart_player"
        }
      ]
}'
