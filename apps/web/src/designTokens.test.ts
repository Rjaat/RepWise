function relativeLuminance(hex: string): number {
  const channels = hex
    .slice(1)
    .match(/.{2}/g)!
    .map((channel) => Number.parseInt(channel, 16) / 255)
    .map((channel) =>
      channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
    )

  return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722
}

function contrast(foreground: string, background: string): number {
  const values = [
    relativeLuminance(foreground),
    relativeLuminance(background),
  ].sort((a, b) => b - a)
  return (values[0] + 0.05) / (values[1] + 0.05)
}

describe('brand token contrast contracts', () => {
  it.each([
    ['ink text on ivory', '#151b1a', '#f7f4ed', 4.5],
    ['secondary text on ivory', '#59615d', '#f7f4ed', 4.5],
    ['ink text on gold buttons', '#151b1a', '#c7a76c', 4.5],
    ['ivory text on ink', '#f7f4ed', '#151b1a', 4.5],
    ['dark supporting text on ink', '#c5cbc5', '#151b1a', 4.5],
    ['white text on destructive controls', '#ffffff', '#a33434', 4.5],
  ])('%s meets its minimum ratio', (_, foreground, background, minimum) => {
    expect(contrast(foreground, background)).toBeGreaterThanOrEqual(minimum)
  })
})
