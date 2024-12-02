import synapseclient
import inspect

syn = synapseclient.Synapse()
print("Methods available in Synapse client:")
for method_name in dir(syn):
    if not method_name.startswith('_'):
        print(method_name)