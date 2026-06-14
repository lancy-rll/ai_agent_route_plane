from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from backend.tools.tools import search_poi_around, geocode, get_driving_route, simple_geocode
from backend.agent.state import State
from backend.model.factory import visual_model, chat_model
from backend.rag.retriever import RerankRetriever
from backend.rag.vectorstore import load_vectorstore
from langchain_core.messages import HumanMessage, AIMessage
from backend.utils.prompt_load import load_intent_prompts, load_image_prompts, load_eval_prompts
import json
from langgraph.types import interrupt

IMAGE_ANALYSIS_PROMPT=load_image_prompts()
INTENT_PROMPT=load_intent_prompts()
EVAL_PROMPT=load_eval_prompts()

_vectorstore = load_vectorstore("rag/chroma.db")
retriever = RerankRetriever(_vectorstore)

async def understand_image(state):
    if not state["image_base64"]:
        return {}
    llm=visual_model
    msg=HumanMessage(content=[
        {"type":"text",
         "text":IMAGE_ANALYSIS_PROMPT},
        {"type":"image_url",
         "image_url":{"url":f"data:image/png;base64,{state['image_base64']}"}
        }
    ])

    response=await llm.ainvoke([msg])

    desc = response.content
    enhanced_query = state["user_query"]
    if desc:
        enhanced_query = f"{state['user_query']}\n【图片信息】{desc}" if state["user_query"] else desc
    return {"image_description": desc, "user_query": enhanced_query}


async def understand_intent(state):
    prompt=ChatPromptTemplate.from_template(INTENT_PROMPT)
    llm=chat_model
    chain=prompt|llm|JsonOutputParser()
    try:
        result=await chain.ainvoke({"user_query":state["user_query"]})
        
        print(f"[DEBUG] understand_intent - LLM 原始返回: {result}")
        
        if isinstance(result, str):
            print(f"[WARNING] JsonOutputParser 返回字符串，尝试手动解析")
            import json
            result = json.loads(result)
        
        intent = result.get("intent", "general_chat") if isinstance(result, dict) else "general_chat"
        slots = result.get("slots", {}) if isinstance(result, dict) else {}
        
        if not isinstance(slots, dict):
            slots = {}
            
        print(f"[DEBUG] understand_intent - intent: {intent}, slots: {slots}")
        return {"intent": intent, "extracted_slots": slots}
    except Exception as e:
        print(f"[ERROR] understand_intent 失败: {e}")
        import traceback
        traceback.print_exc()
        return {"intent": "general_chat", "extracted_slots": {}}

async def retrieve_knowledge(state):
    slots = state["extracted_slots"]
    origin = slots.get("origin", "")
    destination = slots.get("destination", "")
    keyword = slots.get("keyword", "")

    queries = [f"{origin} 到 {destination} 沿途 交通管制 道路封闭 施工"]
    if keyword:
        queries.append(f"{origin} 附近 {keyword}")

    all_docs = []
    seen_contents = set()
    for q in queries:
        docs = retriever.retrieve(q, top_n=5)
        for doc in docs:
            if doc.page_content not in seen_contents:
                all_docs.append(doc)
                seen_contents.add(doc.page_content)

    knowledge = "\n\n".join([doc.page_content for doc in all_docs[:5]])
    return {"retrieved_knowledge": knowledge}


async def plan_routes(state):
    slots = state["extracted_slots"]
    intent = state["intent"]
    user_query = state["user_query"]
    
    print(f"[DEBUG] plan_routes 被调用 - intent: {intent}, user_query: {user_query}, slots: {slots}")

    if not isinstance(slots, dict):
        slots = {}

    if intent == "route_plan":
        origin_name = slots.get("origin")
        dest_name = slots.get("destination")
        
        print(f"[DEBUG] route_plan - origin: {origin_name}, destination: {dest_name}")
        
        if not origin_name or not dest_name:
            if "到" in user_query:
                parts = user_query.split("到")
                if len(parts) >= 2:
                    origin_name = parts[0].strip()
                    dest_name = parts[1].strip()
                    print(f"[DEBUG] 简单解析结果 - origin: {origin_name}, destination: {dest_name}")
        
        if not origin_name or not dest_name:
            return {"candidate_routes": [], "final_response": "请提供明确的起点和终点，例如：从北京到上海怎么走"}

        try:
            print(f"[DEBUG] 正在地理编码: 起点={origin_name}")
            origin_coord = await simple_geocode(origin_name)
            print(f"[DEBUG] 地理编码起点结果: {origin_coord}, 类型: {type(origin_coord)}")
            
            print(f"[DEBUG] 正在地理编码: 终点={dest_name}")
            dest_coord = await simple_geocode(dest_name)
            print(f"[DEBUG] 地理编码终点结果: {dest_coord}, 类型: {type(dest_coord)}")

            print(f"[DEBUG] 正在调用路线规划API")
            route_result = await get_driving_route(
                origin=origin_coord,
                destination=dest_coord,
                avoid_tolls=slots.get("avoid_tolls", False) if isinstance(slots, dict) else False
            )
            
            print(f"[DEBUG] 路线规划API返回: {route_result}, 类型: {type(route_result)}")
            
            routes_list = []
            if isinstance(route_result, dict):
                routes_list = route_result.get("routes", [])
            
            print(f"[DEBUG] 解析到 {len(routes_list)} 条路线")
            
            routes = []
            for i, route in enumerate(routes_list):
                if isinstance(route, dict):
                    routes.append({
                        "type": "route",
                        "id": f"route_{i}",
                        "summary": route.get("summary", f"路线{i+1}"),
                        "distance": route.get("distance", 0),
                        "duration": route.get("duration", 0),
                        "polyline": route.get("polyline", ""),
                        "map_url": route.get("map_url", ""),
                        # 添加坐标信息
                        "origin_coord": origin_coord,
                        "dest_coord": dest_coord
                    })
            
            print(f"[DEBUG] 最终路线列表: {routes}")
            
            if not routes:
                return {"candidate_routes": [], "final_response": f"我正在帮您查找从{origin_name}到{dest_name}的路线，当前网络可能有些延迟，或者您可以换个方式描述起点和终点再试试？"}
                
            return {"candidate_routes": routes}
        except Exception as e:
            print(f"[ERROR] plan_routes 失败: {e}")
            import traceback
            traceback.print_exc()
            return {"candidate_routes": [], "final_response": f"抱歉，在规划路线时遇到了问题：{str(e)}。请检查网络连接或稍后再试。"}

    elif intent == "poi_search":
        location_name = slots.get("location") or slots.get("origin")
        keyword = slots.get("keyword")
        radius = slots.get("radius", 2000)

        print(f"[DEBUG] poi_search - location: {location_name}, keyword: {keyword}")
        
        if not location_name or not keyword:
            return {"candidate_routes": [], "final_response": "请告诉我您想在哪儿搜索什么，例如：天安门附近的停车场"}

        try:
            center_coord = await simple_geocode(location_name)
            pois = await search_poi_around.ainvoke({"location": center_coord, "keywords": keyword, "radius": radius})
            
            if not isinstance(pois, list):
                pois = []
                
            print(f"[DEBUG] 找到 {len(pois)} 个POI")
                
            return {"candidate_routes": pois}
        except ValueError as e:
            return {"candidate_routes": [], "final_response": str(e)}
        except Exception as e:
            print(f"[ERROR] poi_search 失败: {e}")
            import traceback
            traceback.print_exc()
            return {"candidate_routes": [], "final_response": f"地点搜索失败: {str(e)}"}

    return {}

async def evaluate_and_optimize(state):
    routes = state["candidate_routes"]
    final_response = state.get("final_response")
    intent = state.get("intent", "")
    
    print(f"[INFO] evaluate_and_optimize - routes: {routes}")
    print(f"[INFO] evaluate_and_optimize - user_query: {state['user_query']}")
    print(f"[INFO] evaluate_and_optimize - extracted_slots: {state['extracted_slots']}")
    print(f"[INFO] evaluate_and_optimize - final_response: {final_response}")
    print(f"[INFO] evaluate_and_optimize - intent: {intent}")
    
    # 调试：打印完整路线数据
    for i, route in enumerate(routes):
        print(f"[DEBUG] 路线 {i}: {route}")
        if isinstance(route, dict):
            print(f"  - type: {route.get('type')}")
            print(f"  - summary: {route.get('summary')}")
            print(f"  - map_url: {route.get('map_url')}")
            print(f"  - distance: {route.get('distance')}")
            print(f"  - duration: {route.get('duration')}")

    if final_response:
        return {"final_response": final_response}

    if not routes:
        if intent == "poi_search":
            return {"final_response": "没有找到相关的地点，请调整搜索关键词或位置。"}
        elif intent == "route_plan":
            return {"final_response": "没有找到可行的路线，请调整起终点或偏好。"}
        else:
            return {"final_response": "抱歉，我无法处理这个请求。"}

    is_poi_search = len(routes) > 0 and routes[0].get("type") == "poi"
    
    if len(routes) == 1:
        route = routes[0]
        
        intro_prompt = ChatPromptTemplate.from_template(
            "你是一个路线规划助手。用户请求路线规划，已找到一条路线，请用简洁友好的语言介绍这条路线，并提供地图查看链接。\n路线信息：\n路线: {summary}\n距离: {distance}\n耗时: {duration}\n\n请简洁介绍路线，然后在回复末尾添加一行包含地图链接的文字，格式如下：\n【地图链接】（这里放链接）"
        )
        llm = chat_model
        chain = intro_prompt | llm
        
        # 格式化路线信息
        summary = route.get('summary', '')
        distance = route.get('distance', 0)
        duration = route.get('duration', 0)
        map_url = route.get('map_url', '')
        
        response = await chain.ainvoke({
            "summary": summary,
            "distance": f"{distance/1000:.1f}公里",
            "duration": f"{duration/60:.0f}分钟"
        })
        
        response_text = response.content
        
        # 添加地图链接
        origin_coord = route.get('origin_coord', '')
        dest_coord = route.get('dest_coord', '')
        
        if origin_coord and dest_coord:
            map_link = f"https://uri.amap.com/marker?position={dest_coord}&src=route_planner&callnative=1"
            response_text += f"\n\n📍 **查看路线地图：**\n"
            response_text += f"点击链接在地图上查看：{map_link}\n"
            
            if map_url:
                response_text += f"📷 路线预览图：\n"
                response_text += f"![路线图]({map_url})\n"
        
        print(f"[DEBUG] LLM response = {response_text}")
        return {"final_response": response_text}
    
    if is_poi_search:
        items_summary = "\n".join([
            f"{i+1}. {route.get('name', '')} - {route.get('address', '')}" 
            for i, route in enumerate(routes)
        ])
        
        intro_prompt = ChatPromptTemplate.from_template(
            "你是一个地点搜索助手。用户请求搜索地点，已找到多个相关地点，请用自然友好的语言列出这些选项并引导用户选择。\n地点选项：\n{items_summary}\n请给出简洁的选择引导，不要输出详细说明。"
        )
        llm = chat_model
        intro_resp = await llm.ainvoke(intro_prompt.format_messages(items_summary=items_summary))
        intro_msg = intro_resp.content.strip()

        items_info = "\n".join([
            f"{i+1}. **{route.get('name', '')}** - {route.get('address', '')}"
            for i, route in enumerate(routes)
        ])
        
        response_text = f"{intro_msg}\n\n地点选项：\n{items_info}\n\n请告诉我你想选择哪一个（输入数字1、2或3）？"
    else:
        routes_summary = "\n".join([
            f"{i+1}. {route.get('summary', '')}" 
            for i, route in enumerate(routes)
        ])
        
        intro_prompt = ChatPromptTemplate.from_template(
            "你是一个路线规划助手。用户请求路线规划，已找到多条可行路线，请用自然友好的语言列出这些路线选项并引导用户选择。\n路线选项：\n{routes_summary}\n请给出简洁的路线选择引导，不要输出详细路线说明。"
        )
        llm = chat_model
        intro_resp = await llm.ainvoke(intro_prompt.format_messages(routes_summary=routes_summary))
        intro_msg = intro_resp.content.strip()

        routes_info = []
        for i, route in enumerate(routes):
            route_info = f"{i+1}. **{route.get('summary', '')}**"
            map_url = route.get('map_url', '')
            if map_url:
                route_info += f" 📍"
            routes_info.append(route_info)
        
        response_text = f"{intro_msg}\n\n路线选项：\n" + "\n".join(routes_info) + "\n\n请告诉我你想选择哪一条路线（输入数字1、2或3）？"
        
        # 如果有坐标信息，添加通用地图链接提示
        if routes and routes[0].get('origin_coord') and routes[0].get('dest_coord'):
            origin_coord = routes[0].get('origin_coord', '')
            dest_coord = routes[0].get('dest_coord', '')
            map_link = f"https://uri.amap.com/marker?position={dest_coord}&src=route_planner&callnative=1"
            response_text += f"\n\n📍 点击查看地图概览：{map_link}"
    
    return {"final_response": response_text, "pending_selection": True, "routes": routes}

async def generate_response(state):
    text=state["final_response"] or "抱歉，我暂时无法处理这个请求。"
    return {"messages": [AIMessage(content=text)]}

async def direct_reply(state):
    messages = state.get("message", [])
    conversation_history = "\n".join([
        f"{'用户' if isinstance(msg, HumanMessage) else '助手'}: {msg.content}"
        for msg in messages[:-1]
    ])

    if conversation_history:
        prompt_text = f"""你是一个旅行助手。以下是对话历史：
{conversation_history}

用户最新问题：{state['user_query']}

请基于对话历史回答用户的问题。"""
    else:
        prompt_text = f"你是一个旅行助手，请回答用户问题：{state['user_query']}"

    prompt = ChatPromptTemplate.from_template(prompt_text)
    llm = chat_model
    chain = prompt | llm
    resp = await chain.ainvoke({})
    return {"messages": [AIMessage(content=resp.content)], "final_response": resp.content}
