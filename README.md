# Busybook Generator

This application generates children's busybooks with themed pages, including images and fun facts, using AI models through Amazon Bedrock.

## Features

- Generates busybooks with customizable themes
- Creates cover pages and content pages with AI-generated images and text
- Outputs individual PNG images and a complete PDF busybook
- Utilizes Stability AI Diffusion 1.0 for image generation
- Uses Claude 3 Haiku for text generation

## Requirements

- Python 3.7+
- AWS account with access to Amazon Bedrock
- Required Python packages (see requirements.txt)

## Setup

1. Clone the repository
2. Install the required packages: `pip install -r requirements.txt`
3. Set up your AWS credentials:
    - Create a .env file in the project root
    - Add your AWS credentials:
      ```
      AWS_ACCESS_KEY_ID=your_access_key
      AWS_SECRET_ACCESS_KEY=your_secret_key
      ```
4. Ensure you have the Comic Sans font file (`SF_Cartoonist_Hand.ttf`) in the `./comicsans/` directory.

## Usage

Run the script to generate busybooks: `python main.py`

The script will generate busybooks for predefined themes, each with 20 pages. The output will be saved in the BusyBooks directory.