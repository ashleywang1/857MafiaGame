"""
The Following implementation of Miller-Rabin algorithm was taken from
https://gist.github.com/Ayrx/5884790
"""

import random

def miller_rabin(n, k):

    # Implementation uses the Miller-Rabin Primality Test
    # The optimal number of rounds for this test is 40
    # See http://stackoverflow.com/questions/6325576/how-many-iterations-of-rabin-miller-should-i-use-for-cryptographic-safe-primes
    # for justification

    # If number is even, it's a composite number

    if n == 2:
        return True

    if n % 2 == 0:
        return False

    r, s = 0, n - 1
    while s % 2 == 0:
        r += 1
        s //= 2
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, s, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

if __name__ == '__main__':
    # p_hex = "E1401785C2058A10241FEABE932E3BAF4A802492D6E53A2545FD2BC35C499540251157A12C5584F59C0A42BADA8C91E39A4BCC3A1CE00EA55D98C2F23DEE283329E0929562717AA041CAB9629105FBC40B971683B8CAA9C9C1FDFED2AABE218C4ACD648A86C22A3C24DE3D78D9B0847CF9695AA8564D37F0D5D376422817A1279ABDB454A4ACB78E43108FA4135BC84C4E44DA088CF362292F6E073A0B0EAC39D4C41ACF8FD263F0E4DA2FEA68B2F798C84D09704F6C6FA29C0B8883B70E74644F0610E49881DC443015936F83E11BCDACBF01358D42921D692B1895F25EA5EF75D7ACD3707FE266E10EB36E423AA10FDBC7BD2F81755C873125639C16C80419"
    p_hex = "FB0ECABBB1897BDE4862BDD74EF53B26D853E3840F9505A030E2C462D777B28D353CBFA959BBD08AF39D300BDE5622173CC05C3E4ED18550D34A36EDF440AE20B086F9366A79517344D6366E2F5B64D3E18BC19F16332EAB76107CB9922BB654DB7D6389DAF033F21596717669DD0E703EDF5F90334F9F1D6956BE6D1907260E45568E2781F1B771BE335A4341DFECBA2C150545DC9D1AEEE2FC5CC7976770C39735B7DAA25B8A0E3947A37B56D387060F76D0524687A1A3357AB9587F6164A9A3D82F352B136318802922A672CB9950A3BC9991EE9871C14615F0B09EF50290A74985B52F4352C557BA2505C78D47D6D4A5EBA9F925CD2FE2D477B3D6FB2BC7"
    p_int = int(p_hex, 16)
    is_prime = miller_rabin(p_int, 40)

    q_int = 2*p_int+1
    is_prime2 = miller_rabin(q_int, 40)

    print('prime?:', is_prime)
    print('prime2?:', is_prime2)