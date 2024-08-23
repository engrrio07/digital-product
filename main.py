import json
import os
from dotenv import load_dotenv
import logging
import boto3
import base64
from PIL import Image
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
import re
from reportlab.lib.colors import lightyellow, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import random

pdfmetrics.registerFont(TTFont('ComicSans', './comicsans/SF_Cartoonist_Hand.ttf'))

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Initialize Bedrock client
bedrock = boto3.client(
    service_name='bedrock-runtime', 
    region_name='us-east-1', 
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

def generate_image(prompt, negative_prompt, stylePreset):
    """Generate an image using Stability AI Diffusion 1.0 model through Amazon Bedrock."""
    model_id = 'stability.stable-diffusion-xl-v1'
    
    request_body = json.dumps({
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1
            },
            {
                "text": negative_prompt,
                "weight": -1
            }
        ],
        "cfg_scale": 10,
        "seed": random.randint(0, 4294967295),
        "steps": 50,
        "samples": 1,
        "style_preset": stylePreset
    })

    try:
        response = bedrock.invoke_model(
            body=request_body,
            modelId=model_id,
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'artifacts' in response_body and len(response_body['artifacts']) > 0:
            base64_image = response_body['artifacts'][0]['base64']
            image_data = base64.b64decode(base64_image)
            image = Image.open(io.BytesIO(image_data))
            
            return image
        else:
            logger.warning(f"No image was generated. Response: {response_body}")
            return None
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        return None
    
def generate_text(prompt):
    try:
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": f"You are a helpful assistant creating content for children's busy books. {prompt}"
                }
            ]
        })

        response = bedrock.invoke_model(
            body=body,
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            contentType='application/json',
            accept='application/json'
        )

        response_body = json.loads(response['body'].read())
        text = response_body['content'][0]['text'].strip()
        
        # Extract text after the colon
        colon_index = text.find(':')
        if colon_index != -1:
            text = text[colon_index + 1:].strip()
        else:
            # If no colon is found, remove common introductory phrases
            text = re.sub(r'^(Here\'s a|Here is a|Sure,|Certainly,)\s*', '', text, flags=re.IGNORECASE)
        
        return text
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

def create_cover_page(pdf_canvas, theme, output_folder):
    """Create a colorful cover page for the coloring book."""
    width, height = letter
    
    # Generate a colorful image for the cover
    cover_prompt = f"A vibrant and colorful {theme} themed children's coloring book cover"
    cover_image = generate_image(cover_prompt, negative_prompt="blurry, distorted, texts, words, letters", stylePreset="digital-art")

    # Create theme folder for individual images
    theme_folder = os.path.join(output_folder, theme)
    os.makedirs(theme_folder, exist_ok=True)
    
    if cover_image:
        # Save individual image
        image_filename = f"{theme}_cover.png"
        image_path = os.path.join(theme_folder, image_filename)
        cover_image.save(image_path)
        # Draw the colorful background image
        pdf_canvas.drawImage(ImageReader(cover_image), 0, 0, width=width, height=height)
    
    # Add a semi-transparent overlay to ensure text readability
    pdf_canvas.setFillColor(Color(1, 1, 1, alpha=0.3))
    pdf_canvas.rect(0, 0, width, height, fill=1, stroke=0)
    
    pdf_canvas.showPage()

def create_busybook_page(pdf_canvas, image, text, page_number):
    """Create a single page of the busybook with a smaller, auto-adjusting colored textbox for fun facts."""
    pdf_canvas.setPageSize(letter)
    width, height = letter

    # Add the image
    img_width, img_height = image.size
    aspect = img_height / float(img_width)
    display_width = width - 2*inch
    display_height = display_width * aspect
    pdf_canvas.drawImage(ImageReader(image), inch, height - display_height - inch, width=display_width, height=display_height, mask='auto')

    # Create styles
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontName='ComicSans', alignment=TA_LEFT, textColor=black, fontSize=16)
    text_style = ParagraphStyle('BodyText', parent=styles['BodyText'], fontName='ComicSans', textColor=black, fontSize=12)

    # Create content
    header = Paragraph("Fun Fact:", header_style)
    fact = Paragraph(text, text_style)

    # Calculate required height
    available_width = width - 2.2*inch
    _, header_height = header.wrap(available_width, height)
    _, fact_height = fact.wrap(available_width, height)
    total_height = header_height + fact_height + 0.3*inch  # Add some padding

    # Create a colored textbox for the fun fact
    textbox_width = width - 2*inch
    pdf_canvas.setFillColor(lightyellow)
    pdf_canvas.rect(inch, inch, textbox_width, total_height, fill=1)

    # Add the "Fun Fact 💡" header
    header.drawOn(pdf_canvas, 1.1*inch, 1*inch + total_height - header_height)

    # Add the fun fact text
    fact.drawOn(pdf_canvas, 1.1*inch, 1.1*inch)

    # Add page number
    pdf_canvas.setFillColor(black)
    pdf_canvas.drawString(width/2, 0.5*inch, f"Page {page_number}")
    
    pdf_canvas.showPage()


def generate_busybook(theme, num_pages, output_folder):
    """Generate a complete busybook PDF with a cover page."""
    output_filename = f"{theme}_busybook.pdf"
    full_path = os.path.join(output_folder, output_filename)
    
    pdf_canvas = canvas.Canvas(full_path, pagesize=letter)

    # Create theme folder for individual images
    theme_folder = os.path.join(output_folder, theme)
    os.makedirs(theme_folder, exist_ok=True)
    
    # Create cover page
    create_cover_page(pdf_canvas, theme, output_folder)
    
    for page in range(1, num_pages + 1):
        image_prompt = f"Generate a simple clear with thick lines black and white line random drawing of {theme} movie suitable for a childrens coloring book, page {page}."
        negative_prompt = "blurry, blackout, distorted, shading, texts, words, color, details, realism, photorealistic, complex details"
        text_prompt = f"Generate a unique short, random fun fact about {theme} for children aged 5-7, related to page {page} of a coloring book. Keep it under 50 words."

        image = generate_image(image_prompt, negative_prompt, stylePreset="line-art")
        text = generate_text(text_prompt)

        if image:
            # Save individual image
            image_filename = f"{theme}_page_{page}.png"
            image_path = os.path.join(theme_folder, image_filename)
            image.save(image_path)
            create_busybook_page(pdf_canvas, image, text, page)
        else:
            logger.warning(f"Skipping page {page} due to image generation failure")

    pdf_canvas.save()
    logger.info(f"Busybook created: {full_path}")

if __name__ == "__main__":
    themes = ["Under the Sea Wonders", "Jungle Adventure", "Space Exploration", "Dinosaur Discovery", "Animals"]
    num_pages = 20
    output_folder = "BusyBooks"
    
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    for theme in themes:
        generate_busybook(theme, num_pages, output_folder)
