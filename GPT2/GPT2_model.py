# -*- coding: utf-8 -*-
"""GPT2_model.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/17r2qNJzcwqyyKyisnGxOpcRgsfE2z8QF

Install Required Libraries
"""

!pip install transformers datasets scikit-learn torch

"""Import Libraries and Prepare Data"""

from google.colab import files
import pandas as pd
from sklearn.model_selection import train_test_split
from transformers import GPT2Tokenizer, GPT2ForSequenceClassification, Trainer, TrainingArguments
import torch
from torch.utils.data import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

# Upload the dataset
uploaded = files.upload()

# Load the datasets into pandas DataFrames
train_df = pd.read_csv('xstest_train_clean.csv')
test_df = pd.read_csv('xstest_test_clean.csv')

# Use the correct column names 'prompt' for text and 'label' for labels
train_texts, val_texts, train_labels, val_labels = train_test_split(
    train_df['prompt'], train_df['label'], test_size=0.2, random_state=42)

# Test set (already separated, no need for further split)
test_texts = test_df['prompt']
test_labels = test_df['label']

# Ensure that the texts are converted to a list format
train_texts = train_texts.tolist()  # Convert Pandas Series to list
val_texts = val_texts.tolist()
test_texts = test_texts.tolist()

"""Tokenize the Data"""

# Load GPT-2 tokenizer
tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
tokenizer.pad_token = tokenizer.eos_token  # Ensure eos_token is used as the padding token

# Tokenize data
def preprocess_data(texts):
    return tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")

# Tokenize train, validation, and test data
train_encodings = preprocess_data(train_texts)
val_encodings = preprocess_data(val_texts)
test_encodings = preprocess_data(test_texts)

"""Create a PyTorch Dataset"""

# Check that the lengths of encodings and labels match
assert len(train_encodings['input_ids']) == len(train_labels), "Mismatch between input encodings and labels"
assert len(val_encodings['input_ids']) == len(val_labels), "Mismatch between validation encodings and labels"
assert len(test_encodings['input_ids']) == len(test_labels), "Mismatch between test encodings and labels"

# Ensure labels are lists or tensors
train_labels = train_labels.tolist() if isinstance(train_labels, pd.Series) else train_labels
val_labels = val_labels.tolist() if isinstance(val_labels, pd.Series) else val_labels
test_labels = test_labels.tolist() if isinstance(test_labels, pd.Series) else test_labels

# Create TextDataset class with improved error handling
class TextDataset(Dataset):
    def __init__(self, encodings, labels):
        assert len(encodings['input_ids']) == len(labels), "Encodings and labels must have the same length"
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        # Ensure valid index access
        if idx >= len(self.labels):
            raise IndexError(f"Index {idx} out of bounds for dataset of length {len(self.labels)}")

        item = {key: torch.tensor(val[idx]).clone().detach() for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx]).clone().detach()
        return item

    def __len__(self):
        return len(self.labels)

# Create dataset objects for train, validation, and test sets
train_dataset = TextDataset(train_encodings, train_labels)
val_dataset = TextDataset(val_encodings, val_labels)
test_dataset = TextDataset(test_encodings, test_labels)

"""Load the GPT-2 Model for Classification"""

# Load pre-trained GPT-2 model for sequence classification
model = GPT2ForSequenceClassification.from_pretrained('gpt2', num_labels=2)
model.config.pad_token_id = tokenizer.pad_token_id  # Ensure padding is aligned with the tokenizer

"""Define Evaluation Metrics"""

# Define custom metrics function for evaluation
def compute_metrics(pred):
    labels = pred.label_ids
    preds = pred.predictions.argmax(-1)

    precision, recall, f1, _ = precision_recall_fscore_support(labels, preds, average='binary')
    acc = accuracy_score(labels, preds)

    return {"accuracy": acc, "precision": precision, "recall": recall, "f1": f1}

"""Set Training Arguments"""

# Set training arguments
training_args = TrainingArguments(
    output_dir='./results',
    evaluation_strategy="epoch",  # Evaluate at the end of each epoch
    logging_strategy="epoch",
    save_strategy="epoch",  # Save at the end of each epoch
    learning_rate=2e-5,  # Standard learning rate
    per_device_train_batch_size=4,  # Adjust according to GPU memory
    per_device_eval_batch_size=8,
    num_train_epochs=5,  # Run for 3 epochs
    weight_decay=0.01,
    warmup_steps=500,  # Warmup learning rate
    fp16=False,  # Mixed precision disabled for simplicity
    save_total_limit=2  # Limit saved checkpoints
)

"""Train the Model"""

# Set up Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics  # Use custom metric function
)

# Train the model
trainer.train()

"""Save the Trained Model"""

# Save the model and tokenizer to your Google Drive
model.save_pretrained('/content/drive/MyDrive/GPT_xstest_full')
tokenizer.save_pretrained('/content/drive/MyDrive/GPT_xstest_full')

"""Reload the Saved Model"""

# Reload the saved model and tokenizer
from transformers import GPT2Tokenizer, GPT2ForSequenceClassification

# Load the saved GPT model and tokenizer
model = GPT2ForSequenceClassification.from_pretrained('/content/drive/MyDrive/GPT_xstest_full')
tokenizer = GPT2Tokenizer.from_pretrained('/content/drive/MyDrive/GPT_xstest_full')
model.config.pad_token_id = tokenizer.pad_token_id  # Ensure padding is correctly set

"""Model Evaluation on the Test Set"""

import torch
from datasets import Dataset
from sklearn.metrics import classification_report, confusion_matrix

# Convert test encodings and labels into Dataset format for evaluation
test_dataset = Dataset.from_dict({
    'input_ids': test_encodings['input_ids'],
    'attention_mask': test_encodings['attention_mask'],
    'labels': torch.tensor(test_labels)
})

# Evaluate the model on the test set
results = trainer.evaluate(test_dataset)
print("Test set evaluation results:", results)

# Get the true labels (y_true) from the test set
y_true = test_labels

# Get predictions from the model
predictions = trainer.predict(test_dataset).predictions
y_pred = torch.argmax(torch.tensor(predictions), axis=1)

# Generate confusion matrix
cm = confusion_matrix(y_true, y_pred)
print("Confusion Matrix:\n", cm)

# Generate classification report
print("Classification Report:\n", classification_report(y_true, y_pred, target_names=['Non-Toxic', 'Toxic']))

"""Inference with the Trained Model"""

# Example inference with new data
texts = ["I love programming.", "You are an idiot!"]

# Tokenize the input text
inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)

# Move model to evaluation mode
model.eval()

# Perform inference
with torch.no_grad():
    outputs = model(**inputs)
    logits = outputs.logits
    predictions = torch.argmax(logits, dim=-1)

# Print the predicted classes
labels = ['Non-Toxic', 'Toxic']
for i, text in enumerate(texts):
    print(f"Text: {text}")
    print(f"Predicted Label: {labels[predictions[i]]}\n")