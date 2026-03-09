from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, Tool
from langchain.agents.structured_chat.base import StructuredChatAgent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
import os
from dotenv import load_dotenv
from typing import Dict, Any, List
from pydantic import BaseModel
import json

load_dotenv()

class LocationInput(BaseModel):
    location: str

class HospitalDetailsInput(BaseModel):
    hospitals: List[Dict[str, str]]

class HospitalAgent:
    def __init__(self):
        # Initialize Groq LLM
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.3-70b-versatile",
            temperature=0.7
        )
        
        # Define tools for the agent
        self.tools = [
            Tool(
                name="search_hospitals",
                description="Search for hospitals in a specific location",
                func=self._search_hospitals,
                args_schema=LocationInput
            ),
            Tool(
                name="get_hospital_details",
                description="Get detailed information about specific hospitals",
                func=self._get_hospital_details,
                args_schema=HospitalDetailsInput
            )
        ]
        
        # Create memory with updated configuration
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="output"
        )
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that provides information about hospitals.
            Your role is to help users find hospitals in their area and provide detailed information about them.
            Always provide accurate and up-to-date information."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create agent
        self.agent = StructuredChatAgent.from_llm_and_tools(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
            verbose=True
        )
        
        # Create agent executor with updated memory configuration
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def _search_hospitals(self, location: str) -> List[Dict[str, Any]]:
        """Search for hospitals in a specific location"""
        # This is a placeholder implementation
        # In a real application, this would query a database or API
        return [
            {
                "name": "City Hospital",
                "address": "123 Main St, Bhagalpur",
                "specialties": ["General Medicine", "Cardiology", "Orthopedics"],
                "distance": "2.5 km"
            },
            {
                "name": "Medical Center",
                "address": "456 Health Ave, Bhagalpur",
                "specialties": ["Pediatrics", "Neurology", "Oncology"],
                "distance": "3.8 km"
            }
        ]
    
    def _get_hospital_details(self, hospitals: List[Dict[str, str]]) -> Dict[str, Any]:
        """Get detailed information about specific hospitals"""
        # This is a placeholder implementation
        # In a real application, this would query a database or API
        return {
            "name": "City Hospital",
            "address": "123 Main St, Bhagalpur",
            "phone": "+91-1234567890",
            "email": "info@cityhospital.com",
            "facilities": ["Emergency Care", "ICU", "Laboratory", "Pharmacy"],
            "doctors": ["Dr. Sharma", "Dr. Patel", "Dr. Kumar"]
        }
    
    def get_recommendations(self, location: str) -> str:
        """Get hospital recommendations based on location."""
        try:
            # Format the prompt for hospital recommendations
            prompt = f"""Based on the location '{location}', provide a list of recommended hospitals with the following details for each:
            1. Name of the hospital
            2. Address
            3. Available specialties
            4. Contact information (if available)
            5. Distance from the specified location
            6. Operating hours (if available)

            Format the response as a list of dictionaries with these details.
            Focus on well-known and reputable hospitals in the area.
            For Kolkata, include hospitals like:
            - Apollo Hospital
            - Fortis Hospital
            - AMRI Hospital
            - Peerless Hospital
            - Medica Superspecialty Hospital
            - Narayana Superspeciality Hospital
            - Belle Vue Clinic
            - Woodlands Hospital
            - Ruby General Hospital
            - Columbia Asia Hospital"""

            # Get response from the model
            response = self.llm.invoke(prompt)
            response = response.content if hasattr(response, 'content') else str(response)
            
            # Parse the response into a list of dictionaries
            try:
                # Try to parse as JSON if the response is in JSON format
                hospitals = json.loads(response)
            except json.JSONDecodeError:
                # If not JSON, try to extract information using string manipulation
                hospitals = []
                current_hospital = {}
                
                for line in response.split('\n'):
                    line = line.strip()
                    if not line:
                        if current_hospital:
                            hospitals.append(current_hospital)
                            current_hospital = {}
                        continue
                        
                    if ':' in line:
                        key, value = line.split(':', 1)
                        current_hospital[key.strip()] = value.strip()
                
                if current_hospital:
                    hospitals.append(current_hospital)
            
            return hospitals
            
        except Exception as e:
            print(f"Error getting hospital recommendations: {str(e)}")
            return []

    def get_hospital_details(self, hospitals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get detailed information about hospitals."""
        try:
            # Format the prompt for hospital details
            prompt = f"""Based on the following hospitals, provide detailed information about each:

{hospitals}

For each hospital, provide:
1. Name and location
2. Available specialties
3. Distance from the specified location
4. Contact information (if available)
5. Operating hours (if available)

Format the response as a list of dictionaries with these details."""

            # Get response from the model
            response = self.llm.invoke(prompt)
            response = response.content if hasattr(response, 'content') else str(response)
            
            # Parse the response into a list of dictionaries
            try:
                # Try to parse as JSON if the response is in JSON format
                hospital_details = json.loads(response)
            except json.JSONDecodeError:
                # If not JSON, try to extract information using string manipulation
                hospital_details = []
                current_hospital = {}
                
                for line in response.split('\n'):
                    line = line.strip()
                    if not line:
                        if current_hospital:
                            hospital_details.append(current_hospital)
                            current_hospital = {}
                        continue
                        
                    if ':' in line:
                        key, value = line.split(':', 1)
                        current_hospital[key.strip()] = value.strip()
                
                if current_hospital:
                    hospital_details.append(current_hospital)
            
            return hospital_details
            
        except Exception as e:
            print(f"Error getting hospital details: {str(e)}")
            return [] 