# <Import>

from tkinter import *
from tkinter import messagebox
from tkinter import colorchooser
from PIL import Image, ImageTk, ImageGrab
import json
import os
from datetime import datetime
import openai
from io import BytesIO
import requests
from googletrans import Translator 
import random
import threading
from tkinter.ttk import Progressbar


# <함수>

# 1. 데이터 관리

def save_data(data):
    with open(data_file, 'w') as f:
        json.dump(data, f)

def load_data():
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            return json.load(f)
    return {}

#------------------------------------------
def save_image():
    global current_time, user_image, image_count, img_path, user_folder, image_title
    user_folder = f"user_images/{user_name}"
    os.makedirs(user_folder, exist_ok=True)

    canvas_x = canvas.winfo_rootx()+170
    canvas_y = canvas.winfo_rooty()+100
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()
    
    user_image = ImageGrab.grab(bbox=(canvas_x, canvas_y, canvas_x + canvas_width+50, canvas_y + canvas_height))
    
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    formatted_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # 예: 2023-11-10 15:30:45

    image_count = len(os.listdir(user_folder)) + 1
    # 파일명에 제목과 날짜 추가
    img_path = f"{user_folder}/{image_count}_{image_title}_{current_time}.png"
    user_image.save(img_path)

def load_images():
    images = []
    # 사용자 폴더에서 이미지 파일 목록 가져오기
    for filename in os.listdir(user_folder):
        if filename.endswith(('.png', '.jpg', '.jpeg', '.gif')):  # 이미지 확장자 필터링
            img_path = os.path.join(user_folder, filename)
            img = Image.open(img_path)
            img = img.resize((200, 250))  # 원하는 크기로 조정
            img_tk = ImageTk.PhotoImage(img)  # Tkinter에서 사용할 수 있도록 변환
            # Extract the image title from the filename (the part before the first '_')
            image_title = filename.split('_')[1]  # Assuming the title is stored after the first '_'
            images.append((img_path, img_tk, image_title))  # Include title in the tuple
    return images

#------------------------------------------
def save():
    data['name'] = frame1_name.get()
    data['first_run'] = False 
    save_data(data) 
    os.makedirs(f"user_images/{data['name']}", exist_ok=True)
    frame2()

def save_title():
        global image_title
        image_title = frame4_topic.get()  # 제목 저장
        frame5()  # 다음 단계로 이동


# 2. 그림판

# 그리기 시작할 때 호출되는 함수
def start_draw(event):
    global last_x, last_y
    last_x, last_y = event.x, event.y

# 마우스를 움직일 때 연속적으로 선을 그리는 함수
def paint(event):
    global last_x, last_y
    if last_x is not None and last_y is not None:
        # 이전 위치와 현재 위치를 연결하는 선 그리기
        canvas.create_line(last_x, last_y, event.x, event.y, fill=pen_color, width=pen_size)
    # 현재 위치를 마지막 위치로 업데이트
    last_x, last_y = event.x, event.y

# 마우스 버튼을 놓을 때 그리기를 종료하는 함수
def end_draw(event):
    global last_x, last_y
    last_x, last_y = None, None

def change_color(color):
    global pen_color
    pen_color = color

def choose_color():
    global pen_color
    color_code = colorchooser.askcolor(title="색상 선택")
    if color_code[1]:  # 색상이 선택되었는지 확인
        pen_color = color_code[1]

def size_up():
    global pen_size
    pen_size += 2

def size_down():
    global pen_size
    if pen_size>2:
        pen_size -= 2


# 3. API 관련 함수


def generate_image_from_topic(topic):
    if topic in image_cache:
        return image_cache[topic]  # 캐싱된 이미지 반환

    # 이미지 생성 과정
    translated_topic = translator.translate(topic, src='ko', dest='en').text
    styled_prompt = f"{random.choice(styles)} {translated_topic}"

    response = openai.Image.create(prompt=styled_prompt, n=1, size="256x256")
    image_url = response['data'][0]['url']
    img_response = requests.get(image_url)
    img_data = BytesIO(img_response.content)

    generated_image = Image.open(img_data)
    image_cache[topic] = generated_image  # 캐시에 저장
    return generated_image

def generate_image_async(topic, callback):
    def task():
        image = generate_image_from_topic(topic)
        callback(image)
    threading.Thread(target=task, daemon=True).start()

# DALL-E 모델을 통해 이미지를 생성하는 함수 (번역 포함)
def generate_image_from_topic(topic):
    try:
        # 주제를 영어로 번역
        translated_topic = translator.translate(topic, src='ko', dest='en').text

        # 무작위로 스타일 선택
        styles = [
            "a watercolor painting of", 
            "a colorful illustration of", 
            "a digital artwork of", 
            "a vibrant cartoon drawing of", 
            "an abstract art piece of", 
            "an oil painting of"
        ]
        selected_style = random.choice(styles)

        # 스타일과 주제를 포함한 프롬프트
        styled_prompt = f"{selected_style} {translated_topic}"
        
        # DALL-E API를 사용해 이미지 생성
        response = openai.Image.create(prompt=styled_prompt, n=1, size="256x256")
        image_url = response['data'][0]['url']
        
        # 이미지 다운로드
        img_response = requests.get(image_url)
        img_data = BytesIO(img_response.content)
        return Image.open(img_data)

    except Exception as e:
        messagebox.showerror("이미지 생성 오류", f"이미지 생성 중 오류가 발생했습니다: {e}")
        return None

#-----------------------------------------
def regenerate_image():
    """
    이미지 재생성 버튼 클릭 시 호출됩니다.
    """
    global img_label_0

    # "로딩 중" 메시지 표시
    img_label_0.config(text="이미지를 생성 중입니다...", image="")  # 이미지 대신 텍스트 표시

    def on_image_generated(image):
        if image:
            img_tk = ImageTk.PhotoImage(image)
            img_label_0.config(image=img_tk, text="")  # 생성된 이미지로 교체
            img_label_0.image = img_tk  # 참조 유지
        else:
            img_label_0.config(text="이미지를 생성할 수 없습니다.")  # 실패 메시지 표시

    # 비동기로 이미지 생성
    generate_image_async(image_title, on_image_generated)

#----------------------------------------------
def translate_text(topic):
    if topic in translation_cache:
        return translation_cache[topic]
    translated_topic = translator.translate(topic, src='ko', dest='en').text
    translation_cache[topic] = translated_topic
    return translated_topic

# 긍정적인 피드백을 생성하는 함수
def generate_positive_feedback():
    try:
        prompt_text = "이 작품에 대해 긍정적이고 격려하는 코멘트를 해줘. 친구처럼 편하게 말해줘!\
       그림과 관련없는 얘기를 하면 안돼"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 친구처럼 긍정적이고 격려하는 피드백을 주는 예술 멘토야.\
                 그림과 관련없는 얘기를 하면 안돼"},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=150,  # 더 긴 피드백을 위해 max_tokens 값을 증가
            temperature=1.0
        )
        feedback_text = response.choices[0].message['content'].strip()
        return feedback_text
    except Exception as e:
        messagebox.showerror("피드백 생성 오류", f"피드백 생성 중 오류가 발생했습니다: {e}")
        return "피드백을 생성할 수 없습니다."


# 4. 갤러리

def create_image_grid(frame):
    images = load_images()  # 이미지 로드
    rows = (len(images) + 2) // 3  # 이미지 개수에 따라 행 수 계산 (3개씩 배치)
    cols = 3  # 한 행에 3개

    for r in range(rows):
        for c in range(cols):
            index = r * cols + c
            if index < len(images):  # 이미지가 있는 경우에만 표시
                img_path, img_tk, image_title = images[index]  # 경로, img_tk, 제목을 튜플로 받음
                img_btn = Button(frame, image=img_tk, command=lambda img_path=img_path, image_title=image_title: show_image(img_path, image_title))
                img_btn.image = img_tk  # Button에서 ImageTk 객체에 대한 참조 유지
                img_btn.grid(row=r, column=c, padx=5, pady=5)

def show_image(img_path, image_title):
    top = Toplevel()
    top.title("이미지 보기")

    try:
        # 파일 이름에서 날짜 부분 추출
        img_name = os.path.basename(img_path)
        parts = img_name.split('_')
        
        if len(parts) >= 3:
            title = parts[1]  # 제목 추출
            date_str = parts[2]  # 날짜 추출
            formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            title = "제목 없음"
            formatted_date = "날짜 없음"

        # 이미지 로드 및 크기 조정
        img = Image.open(img_path)
        img = img.resize((400, 500), Image.LANCZOS)
        img_tk_resized = ImageTk.PhotoImage(img)

        img_label = Label(top, image=img_tk_resized)
        img_label.image = img_tk_resized
        img_label.pack()

        # 제목, 날짜, 시간 라벨 추가
        title_label = Label(top, text=f"제목: {title}", font=("나눔고딕OTF", 12, "bold"))
        title_label.pack()
        date_label = Label(top, text=f"날짜: {formatted_date}")
        date_label.pack()

    except IndexError:
        error_label = Label(top, text="정보를 찾을 수 없습니다.", fg="red")
        error_label.pack()

    close_button = Button(top, text="닫기", command=top.destroy)
    close_button.pack(pady=10)

    top.geometry("400x600")


# 5. 설정창

def create_set_btn(parent):
    set_btn = Button(parent, text="설정", fg="white", bg="black", command=open_set_win)
    set_btn.place(relx=0.025, rely=0.05, anchor='center')
    return set_btn

def open_set_win():
    set_win = Toplevel(win)
    set_win.title("설정")
    set_win.geometry("300x200")
    set_win.resizable(False, False)

    set_win_name = Label(set_win, text="이름 변경")
    set_win_name.place(relx=0.2, rely=0.3, anchor='center')
    
    new_name = Entry(set_win) 
    new_name.place(relx=0.5, rely=0.3,width = 100, anchor='center')

    def resave_name():
        global user_name
        data['name'] = new_name.get()
        user_name = new_name.get()
        save_data(data)
        set_win.destroy()
         
    set_win_name_btn = Button(set_win, text="완료", fg="white", bg="black", command=resave_name)
    set_win_name_btn.place(relx=0.8, rely=0.3, anchor='center')


# <프레임>

win = Tk()

win.geometry("1000x500")
win.title("그림 프로그램")
win.option_add("*Font","나눔고딕OTF 13")
win.resizable(False, False)

data_file = 'data.json'
data = load_data()

openai.api_key = "sk-proj-UMrIYuedGxOxKW8nLnj0ptVRrbNuQN-S1Unt1hwbs4TbHtfTMjz2vZmS4\
-rvBOZhZgGmPT1cC_T3BlbkFJ5OUUOYp1Obte9IiYgkHg_F-OgEkMIQknmQiv_a8wOlBtd7W3yKsBDyDbzCsnzT3zX9Pe5d3mgA"
translator = Translator()
translation_cache = {}
image_cache = {}
last_x, last_y = None, None



def frame1():
    global frame1_name
    frame1 = Frame(win, width=1000, height=500)
    frame1.place(x=0, y=0) 
    
    frame1_text = Label(frame1, text = "안녕! 이름이 뭐야?")
    frame1_text.place(relx=0.5, rely=0.4, anchor='center')
    
    frame1_name = Entry(frame1) 
    frame1_name.place(relx=0.5, rely=0.45, anchor='center')

    data['name'] = frame1_name.get()
    data['first_run'] = True
    
    save_data(data)

    frame1_btn = Button(frame1, text = "입력", fg = "white", bg = "black", command = lambda: save())    
    frame1_btn.place(relx=0.5, rely=0.525, anchor='center')
    
def frame2():
    global user_name
    for widget in win.winfo_children():
        widget.destroy()

    data = load_data()
    
    frame2 = Frame(win, width=1000, height=500)
    frame2.place(x=0, y=0)
    
    user_name = data.get('name')
    frame2_text = Label(frame2, text = "반가워 %s!!\n 나는 노스체라고 해.\n 우리 같이 그림을 그려보자!"%user_name)
    frame2_text.place(relx=0.5, rely=0.4, anchor='center')
    
    frame2_btn1 = Button(frame2, text = "사용 방법",fg = "white", bg = "black",
                         width = 10, command = lambda: frame3())
    frame2_btn1.place(relx=0.43, rely=0.55, anchor='center')
    
    frame2_btn2 = Button(frame2, text = "사용 시작",fg = "white", bg = "black",
                         width = 10, command = lambda: frame4())
    frame2_btn2.place(relx=0.56, rely=0.55, anchor='center')


def frame2_2():

    global user_name
    data = load_data()
    
    frame2_2 = Frame(win, width=1000, height=500)
    frame2_2.place(x=0, y=0)
    
    user_name = data.get('name')
    frame2_2_text = Label(frame2_2, text = "안녕 %s!!\n오늘도 같이 그림을 그려보자!"%user_name)
    frame2_2_text.place(relx=0.5, rely=0.4, anchor='center')
    
    frame2_2_btn1 = Button(frame2_2, text = "사용 방법",fg = "white", bg = "black",
                         width = 10, command = lambda: frame3())
    frame2_2_btn1.place(relx=0.43, rely=0.55, anchor='center')
    
    frame2_2_btn2 = Button(frame2_2, text = "사용 시작",fg = "white", bg = "black",
                         width = 10, command = lambda: frame4())
    frame2_2_btn2.place(relx=0.56, rely=0.55, anchor='center')


def frame3():
    for widget in win.winfo_children():
        widget.destroy()

    frame3 = Frame(win, width=1000, height=500)
    frame3.place(x=0, y=0)
    
    frame3_text = Label(frame3, text = """~사용 방법~\n\n
    1.그리고 싶은 주제를 입력한다!\n
    2.노스체가 그려준 그림을 참고해서 나만의 그림을 그려보자!\n
    3.그림을 저장하고 갤러리를 확인해보자!\n\n
    ~아주 작은 팁~\n\n
    노스체는 <Rogers의 무조건적 긍정적 수용의 원리>를 바탕으로\n
    %s의 모든 경험을 있는 그대로 수용하고 존중해!\n
    그림을 그리다가 생기는 실수는 부정적인 경험이지만, 나쁜 경험도 때로는 받아들일 필요가 있지.\n
    '지우개 없는 그림판'을 통해 내면을 솔직하게 표현하고 자기 검열로부터 자유로운 미술 시간을 함께 만들어보자!\n
    노스체는 %s의 어떤 활동이나 감정도 이해해^^\n
    이제는 나에게 솔직해질 시간!"""%(user_name,user_name), font=("나눔고딕OTF", 10))

    
    frame3_text.place(relx=0.5, rely=0.4, anchor='center')
    
    frame3_btn = Button(frame3, text = "사용 시작",fg = "white", bg = "black",
                         width = 10, command = lambda: frame4())
    frame3_btn.place(relx=0.5, rely=0.9, anchor='center')
    create_set_btn(frame3)

def frame4():
    global frame4_topic, image_title
    for widget in win.winfo_children():
        widget.destroy()

    frame4 = Frame(win, width=1000, height=500)
    frame4.place(x=0, y=0)
    
    frame4_text = Label(frame4, text="오늘은 무슨 그림을 그릴까?")
    frame4_text.place(relx=0.5, rely=0.4, anchor='center')
    
    frame4_topic = Entry(frame4) 
    frame4_topic.place(relx=0.5, rely=0.45, anchor='center')
    
    frame4_btn = Button(frame4, text="입력", fg="white", bg="black", command=save_title)    
    frame4_btn.place(relx=0.5, rely=0.525, anchor='center')
    create_set_btn(frame4)

def frame5():
    global canvas, pen_color, pen_size, img_label_0
    
    pen_color = "black"
    pen_size = 6
    for widget in win.winfo_children():
        widget.destroy()
        
    frame5_1 = Frame(win, width=500, height=500, bg = "lightblue")
    frame5_1.pack(side=LEFT)
    
    frame5_2 = Frame(win, width=500, height=500,
    highlightbackground = "black", highlightthickness = 1)
    frame5_2.pack(side=RIGHT)
    
    frame5_1_text = Label(frame5_1, text = "여기는 내가 그린 그림이야")
    frame5_1_text.place(relx=0.5, rely=0.1, anchor='center')

    if image_title in image_cache:
        generated_image = image_cache[image_title]
    else:
        generated_image = generate_image_from_topic(image_title)
    
    if generated_image:
        img_tk_0 = ImageTk.PhotoImage(generated_image)
        img_label_0 = Label(frame5_1, image=img_tk_0)
        img_label_0.image = img_tk_0
        img_label_0.place(relx=0.5, rely=0.5, anchor='center')
    else:
        Label(frame5_1, text="이미지를 생성할 수 없습니다.").place(relx=0.5, rely=0.5, anchor='center')

    
    frame5_1_btn = Button(frame5_1, text="재생성", width=5, fg="white", bg="black", command=regenerate_image)
    frame5_1_btn.place(relx=0.1, rely=0.9, anchor='center')

    canvas = Canvas(frame5_2,width=400, height=500)
    canvas.pack(side = RIGHT)
   
    canvas.bind("<ButtonPress-1>", start_draw)    # 마우스 버튼 눌림
    canvas.bind("<B1-Motion>", paint)            # 마우스 드래그
    canvas.bind("<ButtonRelease-1>", end_draw)

    option_frame = Frame(frame5_2, width = 60, height = 500, bg = 'gray')
    option_frame.pack(side=LEFT)
    
    btn_black = Button(option_frame, width = 5, bg = "black", command = lambda: change_color("black"))
    btn_black.place(x=0, y=0)

    btn_red = Button(option_frame, width = 5, bg = "red", command = lambda: change_color("red"))
    btn_red.place(x=0, y=40)
    
    btn_blue = Button(option_frame, width = 5, bg = "blue", command = lambda: change_color("blue"))
    btn_blue.place(x=0, y=80)
    
    #------------------------
    btn_colors = Button(option_frame, width = 5, text = "다른색", font = ("나눔고딕OTF",'12'),command = choose_color) #색상창함수: 일단 아무거나 넣어둠
    btn_colors.place(x=0, y=120)
    
    #----------------------------                    
    btn_size_up = Button(option_frame, text = "굵게", width = 5, font = ('나눔고딕OTF','12'), command = size_up)
    btn_size_up.place(x=0, y = 160)
    
    btn_size_down = Button(option_frame, text = "가늘게", width = 5, font = ('나눔고딕OTF','12'), command = size_down)
    btn_size_down.place(x=0, y = 200)
    
    frame5_2_btn = Button(option_frame, text = "✓", fg = "white", bg = "black", command=lambda: [save_image(), frame6()])    
    frame5_2_btn.place(relx=0.5, rely=0.9, anchor='center')

    # "이전" 버튼 추가하여 frame4로 돌아가기
    previous_btn = Button(frame5_2, text="이전", fg="white", bg="black", command=lambda: [frame5_1.pack_forget(), frame5_2.pack_forget(), frame4()])
    previous_btn.place(x=0,y=360)

def frame6():
    global user_image
    for widget in win.winfo_children():
        widget.destroy()
    
    frame6 = Frame(win, width=1000, height=500)
    frame6.place(x=0, y=0)

    user_image = user_image.resize((300, 300))
    user_image_tk = ImageTk.PhotoImage(user_image) 

    user_image_print = Label(frame6, image=user_image_tk)
    user_image_print.place(relx=0.5, rely=0.3, anchor='center')
    user_image_print.image = user_image_tk  
    
    frame6_btn1 = Button(frame6, text="갤러리", fg="white", bg="black",
                         width=10, command=lambda: gallery_frame())
    frame6_btn1.place(relx=0.38, rely=0.7, anchor='center')
    
    frame6_btn2 = Button(frame6, text="더 그리기", fg="white", bg="black",
                         width=10, command=lambda: frame4())
    frame6_btn2.place(relx=0.5, rely=0.7, anchor='center')
    
    frame6_btn3 = Button(frame6, text="종료", fg="white", bg="black",
                         width=10, command=lambda: win.destroy())
    frame6_btn3.place(relx=0.62, rely=0.7, anchor='center')

    feedback_text = generate_positive_feedback()
    feedback_label = Label(frame6, text=feedback_text, wraplength=600, justify="center", font=("나눔고딕OTF", 12))
    feedback_label.place(relx=0.5, rely=0.85, anchor="center")

def gallery_frame():
    for widget in win.winfo_children():
        widget.destroy()

    canvas2 = Canvas(win)
    scrollbar = Scrollbar(win, orient="vertical", command=canvas2.yview)
    scrollable_frame = Frame(canvas2)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas2.configure(scrollregion=canvas2.bbox("all")))

    canvas2.create_window((0, 0), window=scrollable_frame, anchor="nw")

    scrollbar.pack(side="right", fill="y")
    canvas2.pack(side="left", fill="both", expand=True)
    canvas2.config(yscrollcommand=scrollbar.set)

    create_image_grid(scrollable_frame)

    gframe_btn1 = Button(scrollable_frame, text="더 그리기", fg="white", bg="black", width=10, command=lambda: frame4())
    gframe_btn1.grid(row=0, column=3, padx=5, pady=5) 

    gframe_btn2 = Button(scrollable_frame, text="종료", fg="white", bg="black", width=10, command=lambda: win.destroy())
    gframe_btn2.grid(row=1, column=3, padx=5, pady=5) 


# <실행>

if data.get('first_run', True): 
    frame1()  
else:
    frame2_2()

    
win.mainloop()

