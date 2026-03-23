def generate_estimate(description, materials, hours, rate):                                                           
    labor_total = hours * rate                                                                                          
    subtotal = materials + labor_total                                                                                  
    profit = subtotal * 0.20                                                                                            
    total = subtotal + profit                                                                                           
                                                                                                                        
    print("\n================================================")                                                         
    print("           CONSTRUCTION JOB ESTIMATE")                                                                       
    print("================================================")                                                           
    print(f"Job Description : {description}")                                                                           
    print("------------------------------------------------")                                                           
    print(f"Materials Cost  : $ {materials:10,.2f}")                                                                    
    print(f"Labor Cost      : $ {labor_total:10,.2f}")                                                                  
    print("                    ------------")                                                                           
    print(f"Subtotal        : $ {subtotal:10,.2f}")                                                                     
    print(f"Profit (20%)    : $ {profit:10,.2f}")                                                                       
    print("                    ------------")                                                                           
    print(f"TOTAL ESTIMATE  : $ {total:10,.2f}")                                                                        
    print("================================================\n")                                                         
                                                                                                                        
# --- MAIN LOOP ---                                                                                                     
while True:                                                                                                             
    user_job = input("Enter the job description: ")                                                                     
    user_mats = float(input("Enter materials cost: "))                                                                  
    user_hours = float(input("Enter labor hours: "))                                                                    
    user_rate = float(input("Enter hourly rate: "))                                                                     
                                                                                                                        
    # Run the function                                                                                                  
    generate_estimate(user_job, user_mats, user_hours, user_rate)                                                       
                                                                                                                        
    # Ask the user if they want to continue                                                                             
    repeat = input("Generate another estimate? (yes/no): ").lower()                                                     
                                                                                                                        
    if repeat != "yes":                                                                                                 
        print("Goodbye!")                                                                                               
        break                                                                
