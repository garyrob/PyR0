import pyr0
import time
from dask.distributed import Client, LocalCluster

if __name__ == '__main__':
    cluster = LocalCluster()
    client = Client(cluster)

    print("loading the ELF...")
    elf_handle = open("elf", mode="rb")
    elf = elf_handle.read()
    tic = time.perf_counter()
    future = client.submit(pyr0.load_image_from_elf, elf)
    image = future.result()
    toc = time.perf_counter()
    print(f"It takes {toc - tic:0.4f} seconds")

    print("assembling the input...")
    input = bytes([33, 0, 0, 0, 2, 0, 0, 0, 193, 0, 0, 0, 8, 0, 0, 0, 182, 0, 0, 0, 138, 0, 0, 0, 205, 0, 0, 0, 80, 0, 0, 0, 133, 0, 0, 0, 90, 0, 0, 0, 55, 0, 0, 0, 33, 0, 0, 0, 217, 0, 0, 0, 22, 0, 0, 0, 160, 0, 0, 0, 77, 0, 0, 0, 95, 0, 0, 0, 229, 0, 0, 0, 121, 0, 0, 0, 46, 0, 0, 0, 59, 0, 0, 0, 43, 0, 0, 0, 194, 0, 0, 0, 32, 0, 0, 0, 157, 0, 0, 0, 140, 0, 0, 0, 30, 0, 0, 0, 142, 0, 0, 0, 163, 0, 0, 0, 157, 0, 0, 0, 167, 0, 0, 0, 109, 0, 0, 0, 174, 0, 0, 0, 87, 0, 0, 0, 67, 0, 0, 0, 84, 0, 0, 0, 104, 0, 0, 0, 105, 0, 0, 0, 115, 0, 0, 0, 32, 0, 0, 0, 105, 0, 0, 0, 115, 0, 0, 0, 32, 0, 0, 0, 97, 0, 0, 0, 32, 0, 0, 0, 109, 0, 0, 0, 101, 0, 0, 0, 115, 0, 0, 0, 115, 0, 0, 0, 97, 0, 0, 0, 103, 0, 0, 0, 101, 0, 0, 0, 32, 0, 0, 0, 116, 0, 0, 0, 104, 0, 0, 0, 97, 0, 0, 0, 116, 0, 0, 0, 32, 0, 0, 0, 119, 0, 0, 0, 105, 0, 0, 0, 108, 0, 0, 0, 108, 0, 0, 0, 32, 0, 0, 0, 98, 0, 0, 0, 101, 0, 0, 0, 32, 0, 0, 0, 115, 0, 0, 0, 105, 0, 0, 0, 103, 0, 0, 0, 110, 0, 0, 0, 101, 0, 0, 0, 100, 0, 0, 0, 44, 0, 0, 0, 32, 0, 0, 0, 97, 0, 0, 0, 110, 0, 0, 0, 100, 0, 0, 0, 32, 0, 0, 0, 118, 0, 0, 0, 101, 0, 0, 0, 114, 0, 0, 0, 105, 0, 0, 0, 102, 0, 0, 0, 105, 0, 0, 0, 101, 0, 0, 0, 100, 0, 0, 0, 32, 0, 0, 0, 119, 0, 0, 0, 105, 0, 0, 0, 116, 0, 0, 0, 104, 0, 0, 0, 105, 0, 0, 0, 110, 0, 0, 0, 32, 0, 0, 0, 116, 0, 0, 0, 104, 0, 0, 0, 101, 0, 0, 0, 32, 0, 0, 0, 122, 0, 0, 0, 107, 0, 0, 0, 86, 0, 0, 0, 77, 0, 0, 0, 90, 0, 0, 0, 82, 0, 0, 0, 115, 0, 0, 0, 129, 0, 0, 0, 167, 0, 0, 0, 101, 0, 0, 0, 18, 0, 0, 0, 87, 0, 0, 0, 91, 0, 0, 0, 83, 0, 0, 0, 98, 0, 0, 0, 111, 0, 0, 0, 74, 0, 0, 0, 65, 0, 0, 0, 151, 0, 0, 0, 141, 0, 0, 0, 101, 0, 0, 0, 20, 0, 0, 0, 220, 0, 0, 0, 16, 0, 0, 0, 184, 0, 0, 0, 172, 0, 0, 0, 230, 0, 0, 0, 167, 0, 0, 0, 248, 0, 0, 0, 219, 0, 0, 0, 253, 0, 0, 0, 19, 0, 0, 0, 48, 0, 0, 0, 121, 0, 0, 0, 128, 0, 0, 0, 78, 0, 0, 0, 36, 0, 0, 0, 110, 0, 0, 0, 166, 0, 0, 0, 254, 0, 0, 0, 143, 0, 0, 0, 239, 0, 0, 0, 29, 0, 0, 0, 183, 0, 0, 0, 17, 0, 0, 0, 31, 0, 0, 0, 243, 0, 0, 0, 193, 0, 0, 0, 183, 0, 0, 0, 235, 0, 0, 0, 139, 0, 0, 0, 85, 0, 0, 0, 203, 0, 0, 0, 182, 0, 0, 0, 252, 0, 0, 0, 248, 0, 0, 0, 239, 0, 0, 0, 9, 0, 0, 0, 175, 0, 0, 0, 243, 0, 0, 0, 126, 0, 0, 0, 65, 0, 0, 0, 102, 0, 0, 0, 9, 0, 0, 0, 209, 0, 0, 0, 162, 0, 0, 0, 86, 0, 0, 0, 52, 0, 0, 0])

    print("running the VM...")
    tic = time.perf_counter()
    future = client.submit(pyr0.execute_with_input, image, input)
    segments, info = future.result()
    toc = time.perf_counter()
    print(f"It takes {toc - tic:0.4f} seconds")
    print(f"There are {len(segments)} segments")

    print("generate the receipt for the 1st segment...")
    tic = time.perf_counter()
    future = client.submit(pyr0.prove_segment, segments[0])
    receipt_1 = future.result()
    toc = time.perf_counter()
    print(f"It takes {toc - tic:0.4f} seconds")

    print("generate the receipt for the 2nd segment...")
    tic = time.perf_counter()
    future = client.submit(pyr0.prove_segment, segments[1])
    receipt_2 = future.result()
    toc = time.perf_counter()
    print(f"It takes {toc - tic:0.4f} seconds")

    print("lift both receipts and then join them...")
    tic = time.perf_counter()
    future_1 = client.submit(pyr0.lift_segment_receipt, receipt_1)
    future_2 = client.submit(pyr0.lift_segment_receipt, receipt_2)
    receipt_1_lifted = future_1.result()
    receipt_2_lifted = future_2.result()
    future =  client.submit(pyr0.join_succinct_receipts, [receipt_1_lifted, receipt_2_lifted])
    receipt_joint = future.result()
    toc = time.perf_counter()
    print(f"It takes {toc - tic:0.4f} seconds")

    print("Join both receipts...")
    tic = time.perf_counter()
    future = client.submit(pyr0.join_segment_receipts, [receipt_1, receipt_2])
    receipt_joint_2 = future.result()
    toc = time.perf_counter()
    print(f"It takes {toc - tic:0.4f} seconds")