current_input = '' #will be replaced with the provided value provided by the script that calls this
list_of_inputs = {} #will be replaced with the provided value provided by the script that calls this
previous_input = '' #will be replaced with the provided value provided by the script that calls this
percentages = []


def main(current_input,list_of_inputs,previous_input,percentages):
    if list_of_inputs == {}:
        list_of_inputs[current_input] = {}
        previous_input = current_input
        return current_input,list_of_inputs,previous_input
    else:
        current_input,list_of_inputs,previous_input = add_to_dict(current_input,list_of_inputs,previous_input)
        percentages = calc_percentages(list_of_inputs,current_input)
        next_element = predict_next_element(percentages,current_input,list_of_inputs)
        
        previous_input = current_input
        return current_input,list_of_inputs,previous_input,next_element


def add_to_dict(current_input,list_of_inputs,previous_input):
    if current_input not in list_of_inputs:
        list_of_inputs[current_input] = {}

    if current_input not in list_of_inputs[previous_input]:
        list_of_inputs[previous_input][current_input] = 1
    else:
        list_of_inputs[previous_input][current_input] += 1

    return current_input,list_of_inputs,previous_input


def calc_percentages(list_of_inputs,current_input):
    percentages = []
    if not list_of_inputs[current_input]:
        return percentages
    else:
        total = sum(list_of_inputs[current_input].values())
        for key, value in list_of_inputs[current_input].items():
            chance = value / total * 100
            percentages.append(chance)
        return percentages

        
def predict_next_element(percentages,current_input,list_of_inputs):
    highest_value = 0
    highest_idx = 0
    idx = 0
    if not percentages:
        return ''
    for i in percentages:
        if i > highest_value:
            highest_value = i
            highest_idx = idx
            idx += 1
        else:
            idx += 1
    next_element = list(list_of_inputs[current_input].keys())[highest_idx]
    return next_element

