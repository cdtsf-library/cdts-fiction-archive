import yaml
import random
import os

FILE_NAME = ''
SAMPLE_K = 3

def set_file_name(name):
    global FILE_NAME
    FILE_NAME = name


def load_meta_data(k=SAMPLE_K):
    # load yaml file
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings', FILE_NAME)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file '{FILE_NAME}' not found in settings directory")

    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file '{FILE_NAME}': {str(e)}")
    except Exception as e:
        raise Exception(f"Error reading file '{FILE_NAME}': {str(e)}")

    qa = []

    for item in data['faq']:
        question = item['question']
        answer = item['answer']
        qa.append({'question': question, 'answer': answer})

    prompt = data['prompt']
    requirements = data['requirements']
    count = data['count']

    if isinstance(count, int):
        count = f", within {count} words"
    else:
        count = ""

    random_qa = random.sample(qa, min(k, len(qa)))

    return prompt, requirements, random_qa, count

