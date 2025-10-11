#!/usr/bin/env python3
"""
Debug script to test source creation and reproduce the 422 error
"""
import json

import requests


# Test data that mimics what the frontend sends
def test_create_text_source():
    """Test creating a text source with minimal data"""
    url = "http://localhost:8000/sources"
    
    # Form data that matches what the frontend sends
    form_data = {
        'type': 'text',
        'content': 'This is a test content for debugging validation',
        'title': 'Debug Test Source',
        'notebooks': '[]',  # Empty array as JSON string
        'transformations': '[]',  # Empty array as JSON string
        'embed': 'true',
        'delete_source': 'false',
        'async_processing': 'true'
    }
    
    print("Testing text source creation...")
    print(f"Sending form data: {form_data}")
    
    try:
        response = requests.post(url, data=form_data)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        else:
            print(f"Success: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_create_link_source():
    """Test creating a link source"""
    url = "http://localhost:8000/sources"
    
    # Form data for a link source
    form_data = {
        'type': 'link',
        'url': 'https://example.com',
        'title': 'Debug Link Test',
        'notebooks': '[]',  # Empty array as JSON string
        'transformations': '[]',  # Empty array as JSON string  
        'embed': 'true',
        'delete_source': 'false',
        'async_processing': 'true'
    }
    
    print("\nTesting link source creation...")
    print(f"Sending form data: {form_data}")
    
    try:
        response = requests.post(url, data=form_data)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            print(f"Response text: {response.text}")
        else:
            print(f"Success: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

def test_create_source_with_notebook():
    """Test creating a source with a notebook specified"""
    url = "http://localhost:8000/sources"
    
    # First let's get available notebooks
    notebooks_response = requests.get("http://localhost:8000/notebooks")
    if notebooks_response.status_code == 200:
        notebooks = notebooks_response.json()
        if notebooks:
            notebook_id = notebooks[0]['id']
            print(f"Using notebook: {notebook_id}")
            
            form_data = {
                'type': 'text',
                'content': 'Test content with specific notebook',
                'title': 'Debug Test With Notebook',
                'notebooks': json.dumps([notebook_id]),  # Notebook array as JSON string
                'transformations': '[]',  # Empty array as JSON string
                'embed': 'true',
                'delete_source': 'false',
                'async_processing': 'true'
            }
            
            print("\nTesting source creation with notebook...")
            print(f"Sending form data: {form_data}")
            
            try:
                response = requests.post(url, data=form_data)
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                if response.status_code != 200:
                    print(f"Response text: {response.text}")
                else:
                    print(f"Success: {response.json()}")
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("No notebooks available")
    else:
        print(f"Failed to get notebooks: {notebooks_response.status_code}")

if __name__ == "__main__":
    test_create_text_source()
    test_create_link_source()  
    test_create_source_with_notebook()