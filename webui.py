import os
import random 
import gradio as gr
import time
from zhconv import convert
from LLM import LLM
from src.cost_time import calculate_time
from openxlab.model import download
import pdb
os.environ["GRADIO_TEMP_DIR"]= './temp'
os.environ["WEBUI"] = "true"


def get_title(title = 'Linly 智能对话系统 (Linly-Talker)'):
    description = f"""
    <p style="text-align: center; font-weight: bold;">
        <span style="font-size: 28px;">{title}</span>
        <br>
        <span style="font-size: 18px;" id="paper-info">
            [<a href="https://github.com/YongXie66/Honor-of-Kings_RolePlay" target="_blank">主页</a>]
        </span>
        <br> 
    </p>
    """
    return description


# 设置默认system
default_system = '你正在扮演王者荣耀里的角色妲己'
# 设置默认的prompt
prefix_prompt = '''请用少于50个字回答以下问题\n\n'''

# 设定默认参数值，可修改
use_ref_video = False
ref_video = None
ref_info = 'pose'
use_idle_mode = False
length_of_audio = 5

@calculate_time
def Asr(audio):
    try:
        question = asr.transcribe(audio)
        question = convert(question, 'zh-cn')
    except Exception as e:
        print("ASR Error: ", e)
        question = '麦克风模式可能音频还未传入，请重新点击一下语音识别即可'
        gr.Warning(question)
    return question

@calculate_time
def TTS_response(text, 
                 inp_ref, prompt_text, prompt_language, text_language, how_to_cut, 
                 question_audio, question, 
                 tts_method = '', save_path = 'answer.wav'):
    if tts_method == 'GPT-SoVITS克隆声音':
        try:
            vits.predict(ref_wav_path = inp_ref,
                            prompt_text = prompt_text,
                            prompt_language = prompt_language,
                            text = text, # 回答
                            text_language = text_language,
                            how_to_cut = how_to_cut,
                            save_path = 'results/answer.wav')
            print(text, tts_method, save_path)
            return 'results/answer.wav', None
        except Exception as e:
            gr.Warning("无克隆环境或者无克隆模型权重，无法克隆声音", e)
            return None, None
    return None, None
@calculate_time
def LLM_response(question_audio, question, 
                 inp_ref = None, prompt_text = "", prompt_language = "", text_language = "", how_to_cut = "", 
                 tts_method = ''):
    answer = llm.generate(question, default_system)
    print(answer)
    driven_audio, driven_vtt = TTS_response(answer, 
                 inp_ref, prompt_text, prompt_language, text_language, how_to_cut, question_audio, question, 
                 tts_method)
    return driven_audio, driven_vtt, answer


@calculate_time
def Talker_response_img(question_audio, method, text, 
                        inp_ref , prompt_text, prompt_language, text_language, how_to_cut,
                        tts_method,
                        source_image,
                        preprocess_type, 
                        is_still_mode,
                        enhancer,
                        batch_size,                            
                        size_of_image,
                        pose_style,
                        facerender,
                        exp_weight,
                        blink_every,
                        fps, progress=gr.Progress(track_tqdm=True)
                    ):

    driven_audio, driven_vtt, answer = LLM_response(question_audio, text,  
                                               inp_ref, prompt_text, prompt_language, text_language, how_to_cut,
                                               tts_method = tts_method)
    # pdb.set_trace()
    if method == 'SadTalker':
        video = talker.test2(source_image,
                        driven_audio,
                        preprocess_type,
                        is_still_mode,
                        enhancer,
                        batch_size,                            
                        size_of_image,
                        pose_style,
                        facerender,
                        exp_weight,
                        use_ref_video,
                        ref_video,
                        ref_info,
                        use_idle_mode,
                        length_of_audio,
                        blink_every,
                        fps=fps)
    else:
        return None
    if driven_vtt:
        return video, driven_vtt, answer
    else:
        return video, answer


def chat_response(system, message, history):
    # response = llm.generate(message)
    response, history = llm.chat(system, message, history)
    print(history)
    # 流式输出
    for i in range(len(response)):
        time.sleep(0.01)
        yield "", history[:-1] + [(message, response[:i+1])]
    return "", history


def clear_session():
    # clear history
    llm.clear_history()
    return '', []

def clear_text():
    return "", ""


GPT_SoVITS_ckpt = "GPT_SoVITS/pretrained_models"
def load_vits_model(gpt_path, sovits_path, progress=gr.Progress(track_tqdm=True)):
    global vits
    print("gpt_sovits模型加载中...", gpt_path, sovits_path)
    all_gpt_path, all_sovits_path = os.path.join(GPT_SoVITS_ckpt, gpt_path), os.path.join(GPT_SoVITS_ckpt, sovits_path)
    vits.load_model(all_gpt_path, all_sovits_path)
    gr.Info("模型加载成功")
    return gpt_path, sovits_path


def webui_setting(talk = True):
    if not talk:
        with gr.Tabs():
            with gr.TabItem('数字人形象设定'):
                source_image = gr.Image(label="Source image", type="filepath")
    else:
        source_image = gr.Image(value='inputs/DaJi.png', label="DaJi image", type="filepath", elem_id="img2img_image", width=256, interactive=False, visible=False)  


    # inp_ref = gr.Textbox(value='./GPT_SoVITS/ref_audio/主人的命令,是绝对的.wav', visible=False)
    inp_ref = gr.Audio(value="GPT_SoVITS/ref_audio/ref_audio.wav", type="filepath", visible=False)
    prompt_text = gr.Textbox(value='主人的命令，是绝对的', visible=False)
    prompt_language = gr.Textbox(value="中文", visible=False)
    text_language = gr.Textbox(value="中文", visible=False)
    how_to_cut = gr.Textbox(value="凑四句一切", visible=False)
    batch_size = gr.Textbox(value=2, visible=False)

    character = gr.Textbox(value='自定义角色', visible=False)
    tts_method = gr.Textbox(value='GPT-SoVITS克隆声音', visible=False)
    asr_method = gr.Textbox(value='Whisper-tiny', visible=False)
    talker_method = gr.Textbox(value='SadTalker', visible=False)
    llm_method = gr.Textbox(value='Qwen', visible=False)
    return  (source_image, 
             inp_ref, prompt_text, prompt_language, text_language, how_to_cut, 
             tts_method, batch_size, character, talker_method, asr_method, llm_method)


def app_chatty():
    with gr.Blocks(analytics_enabled=False, title = 'DaJi_RolePlay') as inference:
        gr.HTML(get_title("Chatty_DaJi~小狐仙🌟陪你聊天"))
        with gr.Row():
            with gr.Column():
                # (source_image, voice, rate, volume, pitch, 
                # am, voc, lang, male, 
                # inp_ref, prompt_text, prompt_language, text_language, how_to_cut,  use_mic_voice,
                # tts_method, batch_size, character, talker_method, asr_method, llm_method)= webui_setting()
                source_image = gr.Image(value='inputs/DaJi.png', type="filepath", elem_id="img2img_image", interactive=False, visible=True)  

            with gr.Column():
                system_input = gr.Textbox(value=default_system, lines=1, label='System (设定角色)', visible=False)
                chatbot = gr.Chatbot(height=400, show_copy_button=True)
                with gr.Group():
                    question_audio = gr.Audio(sources=['microphone','upload'], type="filepath", label='语音对话', autoplay=False)
                    asr_text = gr.Button('🎤 语音识别（语音对话后点击）')
                
                # 创建一个文本框组件，用于输入 prompt。
                msg = gr.Textbox(label="Prompt/问题")
                asr_text.click(fn=Asr,inputs=[question_audio],outputs=[msg])
                
                with gr.Row():
                    sumbit = gr.Button("🚀 发送", variant = 'primary')
                    clear_history = gr.Button("🧹 清除历史对话")
                    
            # 设置按钮的点击事件。当点击时，调用上面定义的 函数，并传入用户的消息和聊天历史记录，然后更新文本框和聊天机器人组件。
            sumbit.click(chat_response, inputs=[system_input, msg, chatbot], 
                         outputs=[msg, chatbot])
            
            # 点击后清空后端存储的聊天记录
            clear_history.click(fn = clear_session, outputs = [msg, chatbot])
            
        # exmaple_setting(asr_method, msg, character, talker_method, tts_method, voice, llm_method)
    return inference


def app_lively():
    with gr.Blocks(analytics_enabled=False, title = 'DaJi_RolePlay') as inference:
        gr.HTML(get_title("lively_DaJi~小狐仙🌟陪你聊天"))
        with gr.Row(equal_height=False):
            with gr.Column(variant='panel'):
                # with gr.Tabs(elem_id="sadtalker_source_image"):
                #         with gr.TabItem('Source image'):
                #             with gr.Row():
                #                 source_image_path = "inputs/DaJi.png" 
                #                 source_image = gr.Image(value=source_image_path, label="DaJi image", type="filepath", elem_id="img2img_image", width=256, interactive=False)                                
                (source_image,  
                inp_ref, prompt_text, prompt_language, text_language, how_to_cut, 
                tts_method, batch_size, character, talker_method, asr_method, llm_method)= webui_setting()
                             
                with gr.Tabs():
                    with gr.TabItem('ASR'):
                        # chatbot = gr.Chatbot(height=400, show_copy_button=True)
                        with gr.Group():
                            question_audio = gr.Audio(sources=['microphone','upload'], type="filepath", label = '语音输入')
                            asr_text = gr.Button('🎤 语音识别（语音输入后点击）')

                with gr.Tabs(): 
                    with gr.TabItem('Text'):
                        # gr.Markdown("## Text Examples")
                        examples =  [
                            ['你好呀，你是谁？'],
                            ['我今天心情很好，来和我聊天吧！'],
                            ['你知道如何应对压力吗？'],
                        ]
                        
                        input_text = gr.Textbox(label="Input Text", lines=5)
                        output_text = gr.Textbox(label="Output Text", lines=8)
                        asr_text.click(fn=Asr,inputs=[question_audio],outputs=[input_text])
                        gr.Examples(
                            examples = examples,
                            inputs = [input_text],
                        )
                        
                        with gr.Row():
                            submit = gr.Button('🚀 发送', elem_id="LLM&sadtalker_generate", variant='primary')
                            clear_history = gr.Button("🧹 清除对话")
                        
                        clear_history.click(fn=clear_text, outputs=[input_text, output_text])
            
            with gr.Column(variant='panel'):
                with gr.Tabs(elem_id="sadtalker_checkbox"):
                    with gr.TabItem('数字人参数设置'):
                        with gr.Accordion("Advanced Settings", open=False):
                            with gr.Row():
                                size_of_image = gr.Radio([256, 512], value=256, label='face model resolution')
                                batch_size = gr.Slider(label="batch size in generation", step=1, maximum=10, value=8) 
                                enhancer = gr.Checkbox(label="GFPGAN as Face enhancer(take a long time)", value=False)        
                                pose_style = gr.Number(value=0, visible=False)
                                exp_weight = gr.Number(value=1, visible=False)
                                blink_every = gr.Checkbox(value=True, visible=False)
                                preprocess_type = gr.Textbox(value='full', visible=False)
                                is_still_mode = gr.Checkbox(value=True, visible=False)
                                facerender = gr.Textbox(value='facevid2vid', visible=False)
                                fps = gr.Number(value=20, visible=False)

                with gr.Tabs(elem_id="sadtalker_genearted"):
                    gen_video = gr.Video(label="Generated video", format="mp4", value='inputs/DaJi_initial.mp4')  # avi,mp4

                submit.click(
                fn=Talker_response_img,
                inputs=[question_audio,
                        talker_method, 
                        input_text, 
                        inp_ref, prompt_text, prompt_language, text_language, how_to_cut, 
                        tts_method,
                        source_image, 
                        preprocess_type,
                        is_still_mode,
                        enhancer,
                        batch_size,                            
                        size_of_image,
                        pose_style,
                        facerender,
                        exp_weight,
                        blink_every,
                        fps], 
                outputs=[gen_video,
                         output_text]
                )
        
    return inference


def success_print(text):
    print(f"\033[1;31;42m{text}\033[0m")

def error_print(text):
    print(f"\033[1;37;41m{text}\033[0m")

if __name__ == "__main__":
    llm_class = LLM(mode='offline')
    try:
        llm = llm_class.init_model('InternLM2', 'InternLM2/InternLM2_7b', prefix_prompt=prefix_prompt)
        success_print("Success!!! LLM模块加载成功，默认使用InternLM2_DaJi模型")
    except Exception as e:
        error_print(f"Error: {e}")
        error_print("如果使用InternLM2_DaJi，请先下载InternLM2模型和安装环境")
    
    try:
        from VITS import *
        vits = GPT_SoVITS()
        gpt_path = "DaJi-e15.ckpt"
        sovits_path = "DaJi_e12_s240.pth"
        load_vits_model(gpt_path, sovits_path)
        success_print("Success!!! GPT-SoVITS模块加载成功，语音克隆默认使用GPT-SoVITS模型")
    except Exception as e:
        error_print(f"GPT-SoVITS Error: {e}")
        error_print("如果使用VITS，请先下载GPT-SoVITS模型和安装环境")
    
    try:
        from TFG import SadTalker
        talker = SadTalker(lazy_load=True)
        success_print("Success!!! SadTalker模块加载成功，默认使用SadTalker模型")
    except Exception as e:
        error_print(f"SadTalker Error: {e}")
        error_print("如果使用SadTalker，请先下载SadTalker模型")
    
    try:
        from ASR import WhisperASR
        asr = WhisperASR('base')
        success_print("Success!!! WhisperASR模块加载成功，默认使用Whisper-base模型")
    except Exception as e:
        error_print(f"ASR Error: {e}")
        error_print("如果使用FunASR，请先下载WhisperASR模型和安装环境")

    gr.close_all()
    demo_chatty = app_chatty()
    demo_lively = app_lively()
    demo = gr.TabbedInterface(interface_list = [ 
                                                demo_chatty,
                                                demo_lively,
                                                ], 
                              tab_names = [
                                            " Chatty_DaJi", 
                                            " Lively_DaJi", 
                                           ],
                              title = "DaJi-RolePlay WebUI")

    demo.queue()
    demo.launch(server_name=ip, # 本地端口localhost:127.0.0.1 全局端口转发:"0.0.0.0"
                server_port=port,
                # 似乎在Gradio4.0以上版本可以不使用证书也可以进行麦克风对话
                # ssl_certfile=ssl_certfile,
                # ssl_keyfile=ssl_keyfile,
                # ssl_verify=False,
                debug=True,
                ) 
